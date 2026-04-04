# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトは、後方互換性のある変更は MAJOR.MINOR.PATCH のセマンティックバージョニングに従います。

次のリリースノートはソースコードからの推測に基づく初期リリースの要約です。

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買・データ基盤・リサーチ・AI 補助機能の基盤的実装を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期エクスポートを追加（data, strategy, execution, monitoring）。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 設定・環境読み込み (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - OS 環境変数は保護され、.env.local の override 時にも上書きされないよう保護機構を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - コメント行、export KEY=val、シングル/ダブルクォート（バックスラッシュエスケープを考慮）、インラインコメントの扱い。
  - Settings クラスを追加し、主要設定プロパティを提供:
    - J-Quants / kabu ステーション / LINE / データベースパス（duckdb/sqlite）/監視設定（pid ファイル、kill flag、閾値）など。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）、LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - 必須環境変数未設定時に _require が ValueError を投げる仕様を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols テーブルから銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算 (calc_news_window) を実装（JST を考慮した UTC naive datetime を返す）。
    - バッチサイズ、記事数・文字数トリム、最大リトライ・指数バックオフ、429/ネットワーク/タイムアウト/5xx のリトライ挙動を実装。
    - レスポンスバリデーション（JSON 抽出・results 構造・コード絞り込み・数値検査）、スコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等的書き込み（該当 code の DELETE → INSERT）。DuckDB の executemany の挙動を考慮して空リスト時の分岐あり。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
    - score_news API を公開。OpenAI API キー解決は引数優先、未指定時は環境変数 OPENAI_API_KEY を参照し未設定は ValueError。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離とマクロニュース LLM センチメントを重み合成して日次の market_regime を算出。
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッド防止）。データ不足時は中立 1.0 を採用。
    - raw_news からマクロキーワードでタイトル抽出（最大件数制限）。
    - OpenAI 呼び出しは JSON Mode、リトライと 5xx の再試行処理を実装。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - レジームスコア合成（MA 重み 70%、マクロ重み 30%、スコアを -1〜1 にクリップ）、閾値によるラベリング（bull/neutral/bear）。
    - market_regime テーブルへの冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）、例外時に ROLLBACK を試行。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照した営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合の曜日ベースのフォールバックを一貫して実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループガード。
    - calendar_update_job により J-Quants API から差分取得→保存（バックフィルと健全性チェックを含む）する処理を実装（jquants_client を利用）。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult dataclass を追加（取得件数 / 保存件数 / 品質問題 / エラー を保持）。
    - ETL 設計方針（差分更新、backfill、品質チェックの扱い）を実装方針として明記。
    - DuckDB 上でのテーブル存在確認、最大日付取得ユーティリティを実装（ETL 処理の下地）。
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

- リサーチ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率など。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 欠落/0 は None）。
    - DuckDB 内の SQL ウィンドウ関数を用いた実装で、外部 API へはアクセスしない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを取得。ホライズン検証あり。
    - calc_ic: スピアマンランク相関による IC 計算（結合・ None 排除・有効レコード数閾値）。
    - rank: 同順位は平均ランクを返す実装（丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージは主要関数を __all__ で公開。

### 変更 (Changed)
- なし（初期実装）

### 修正 (Fixed)
- なし（初期実装）

### セキュリティ (Security)
- OpenAI API キーの取り扱い:
  - score_news / score_regime は api_key 引数優先、未指定時は環境変数 OPENAI_API_KEY へフォールバック。未設定時は ValueError を送出して明示的に失敗させる設計。

### 注意事項 / 実装上の設計ノート
- ルックアヘッドの防止:
  - ニュース集計・レジーム判定・ファクター計算等、多くの関数は datetime.today() / date.today() を直接参照せず、target_date 引数を利用する設計。外部から日付を注入してバックテストのリークを防止するよう配慮。
- API 呼び出しの堅牢化:
  - OpenAI 呼び出しでのリトライ（指数バックオフ）、5xx 判定・フェイルセーフなデフォルト値（ゼロスコア）などを実装し、部分失敗時にシステム全体が停止しないようになっている。
- テスト容易性:
  - _call_openai_api のような内部関数は unittest.mock.patch で差し替え可能なように実装されている。
- DuckDB 互換性:
  - executemany に空リストを渡せない DuckDB の挙動を考慮した分岐や、list 型バインドの安定性を考慮した実装が含まれる。
- DB 書き込みは可能な限り冪等に実装（DELETE → INSERT、ON CONFLICT での更新など）している。

---

今後のリリースでは、以下のような項目が想定されます（案）:
- strategy / execution / monitoring モジュールの具体的な注文ロジック・実行・監視機能の追加
- jquants_client の実装詳細・API コネクタの強化
- テストカバレッジ・CI 設定・ドキュメントの拡充

（本 CHANGELOG はコードベースの実装内容からの推測に基づくため、実際のリリースノートはプロジェクト方針に合わせて調整してください。）