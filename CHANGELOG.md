# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
現在のリリースはパッケージ内の __version__ に合わせた v0.1.0（初回公開）想定です。日付はコード解析時点のものを付記しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース（コードベースの現状から推測して記載）。

### 追加 (Added)
- パッケージのコア構成を実装
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
    - パブリックAPI: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理モジュール (kabusys.config)
  - プロジェクトルート自動検出機能（.git または pyproject.toml を基準）
  - .env / .env.local の自動読み込み（読み込み優先度: OS環境変数 > .env.local > .env）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）
  - .env ファイルパーサを独自実装（export 形式、クォート/エスケープ、インラインコメント等に対応）
  - 環境変数取得用 Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / システム設定をプロパティで取得）
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の有効値チェック

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を基に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得
    - ウィンドウ定義（JSTベース）: 前日 15:00 ～ 当日 08:30 (DuckDB 比較用に UTC naive datetime に変換)
    - バッチ処理（最大 20 銘柄 / コール）とチャンク単位のリトライ（429・タイムアウト・ネットワーク断・5xx を対象に指数バックオフ）
    - レスポンス検証・数値変換・±1.0 クリップ、部分成功時は既存スコアを保護して差し替え（DELETE → INSERT）
    - テスト容易性: _call_openai_api を patch 可能
    - 公開関数: score_news(conn, target_date, api_key=None)
    - ユーティリティ: calc_news_window(target_date)
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定
    - マクロニュースは news_nlp.calc_news_window を用いて窓を決定し、DB からマクロキーワードでフィルタしたタイトルを抽出
    - OpenAI 呼び出しは独自実装、リトライ・フェイルセーフ実装（API 失敗時は macro_sentiment = 0.0）
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 公開関数: score_regime(conn, target_date, api_key=None)

- リサーチ/ファクター計算 (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金など）、バリュー（PER/ROE）を DuckDB SQL で計算
    - 返り値は (date, code) をキーとする dict のリスト
    - 実装関数: calc_momentum, calc_volatility, calc_value
  - feature_exploration モジュール
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリー
    - 実装関数: calc_forward_returns, calc_ic, rank, factor_summary
  - 研究向けユーティリティの公開 (__init__.py) で便利関数を再エクスポート（zscore_normalize 等）

- データ管理モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを起点に営業日判定、前後の営業日探索（一貫した DB 優先のフォールバック実装）
    - get_trading_days / is_trading_day / next_trading_day / prev_trading_day / is_sq_day を実装
    - calendar_update_job: J-Quants API から差分取得 → market_calendar に冪等保存、バックフィルおよび健全性チェックを実装
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラーの集約）
    - 差分更新・バックフィル・品質チェックのためのユーティリティ関数と内部ヘルパーを実装
    - data.etl で ETLResult を再エクスポート

### 変更点・設計上の注意 (Changed / Notes)
- 全体的な設計方針（共通）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を内部処理の基準として直接参照しない設計になっている（外部から target_date を注入して評価する想定）
  - OpenAI 呼び出しについては JSON mode を使用し、レスポンスの堅牢な検証を行う
  - API 失敗時は例外を即座に上げずフォールバック（0.0 やスキップ）して処理を継続する方針（フェイルセーフ）
  - DuckDB のバージョン差異や空リストバインド問題への対処（executemany 前に空チェック等）を行っている

- 環境変数ロードの挙動
  - OS の環境変数は保護され、.env(.local) の override 挙動は protected set に基づいている
  - .env のパースは export 形式・クォート・エスケープ・インラインコメントなどを考慮している

- ロギングと診断
  - 各処理で詳細な logger.debug / info / warning / exception を出力するように実装されている（観測性に配慮）

### 修正・改善 (Fixed / Improved)
- OpenAI API 呼び出し周りでの耐障害性を強化
  - 429、ネットワーク断、タイムアウト、5xx について指数バックオフでリトライ
  - APIError の status_code が存在しない場合にも安全に扱うロジックを追加
  - レスポンスの JSON パースで余分な前後テキストが混入したケースを復元してパースを試みる実装

- ニュース集約・トリム処理
  - 1 銘柄あたりの最大記事数・最大文字数制限を設け、プロンプト肥大化を回避
  - レスポンス検証で予期しない型や未知の銘柄コードを無視することで部分失敗の影響を抑制

- DuckDB を用いた SQL 実装の堅牢化
  - 欠損データ（NULL）やデータ不足時の挙動を明示（例: MA200 データ不足なら中立扱い）
  - window/lag/lead 集計を SQL で実装し、効率的に計算

### 既知の制約 / 必要な環境 (Known limitations / Requirements)
- OpenAI API キーが必要
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必須で参照。未設定時は ValueError を送出する。
- DuckDB 接続と期待されるテーブル群が必要
  - news_nlp: raw_news, news_symbols, ai_scores
  - regime_detector: prices_daily, raw_news, market_regime
  - research/factor: prices_daily, raw_financials
  - calendar_management: market_calendar
- Slack / kabu ステーション等の外部連携情報は Settings で環境変数から取得（未設定時は ValueError）
- 日時はすべて date / datetime オブジェクトで扱い、timezone の混入を避ける設計

### 廃止・破壊的変更 (Deprecated / Removed / Breaking changes)
- 初版のため該当なし。

---

備考:
- 本 CHANGELOG は与えられたコードベースの実装内容と設計コメントから推測して作成しています。実際のリリースノート作成時はコミット履歴・変更差分・Issue 等を基に正確な差分を記載してください。