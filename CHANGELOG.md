# Changelog

すべての注目すべき変更を記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買／データ基盤／リサーチ支援ライブラリのコア機能を追加しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（バージョン 0.1.0）。モジュール公開: data, strategy, execution, monitoring。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 環境設定・読み込み (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索し決定（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS 環境変数を保護するためにロード時に既存キーを protected として扱う。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱いなど堅牢にパース。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / LINE / DB パス / 監視設定 / システム設定など多数のプロパティを定義。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の値検証。
    - 各種パスは Path 型で返す（expanduser 対応）。
    - is_live / is_paper / is_dev 等のユーティリティプロパティを提供。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を使い、ターゲット日の前日 15:00 JST ～ 当日 08:30 JST に該当する記事群を銘柄ごとに集約。
    - 1 銘柄あたり最大記事数および最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/チャンク）。JSON Mode を利用して厳密な JSON を期待。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証ロジックを実装（JSON 抽出、results 配列検証、コード存在確認、数値チェック）。
    - スコアは ±1.0 にクリップ。取得したスコアを ai_scores テーブルへ部分置換（対象コードのみ DELETE → INSERT）して冪等性を確保。
    - DuckDB の executemany の挙動に配慮し、空パラメータの挿入を回避するガードを実装。
    - テストしやすさのため OpenAI 呼び出し箇所はパッチ差し替え可能（_call_openai_api の抽象化）。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() を内部で参照しない設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次で regime_score / regime_label (bull/neutral/bear) を計算。
    - マクロ記事はあらかじめキーワードでフィルタして最大件数まで抽出。記事がなければ LLM を呼ばず macro_sentiment=0.0。
    - OpenAI 呼び出し時のリトライ・5xx ハンドリング・レスポンスパース失敗時のフォールバック（macro_sentiment=0.0）。
    - レジーム情報は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等的に書き込み。失敗時は ROLLBACK を試行して上位へ例外伝播。
    - テスト容易性: news_nlp と異なる独立した _call_openai_api 実装によりモジュール結合を回避。

- データ（Data Platform）
  - カレンダー管理モジュール（kabusys.data.calendar_management）
    - JPX カレンダーに基づく営業時間判定・次/前営業日取得・期間内営業日一覧取得・SQ 日判定ロジックを提供。
    - market_calendar テーブルが未取得の場合は曜日（土日）ベースでフォールバックする一貫した挙動。
    - next_trading_day / prev_trading_day の最大探索日数制限を設定し無限ループを防止（_MAX_SEARCH_DAYS）。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を行う方針での骨組みを実装。
    - ETLResult: 取得/保存件数、品質問題（QualityIssue のリスト）、エラー一覧、シリアライズ to_dict を提供。
    - DuckDB テーブル存在チェックや最大日付取得などの内部ユーティリティを追加。
    - ETL は id_token 等の注入を想定してテスト容易性を確保する設計方針。

- リサーチ（Research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20 日）、平均売買代金、出来高比率、PER/ROE（raw_financials ベース）等を計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - 不足データの扱い: 条件不足の場合は None を返す設計。
    - DuckDB を用いた SQL ベース実装で外部 API 呼び出しは行わない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（デフォルトホライズン: 1,5,21 営業日）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク変換して算出）。
    - rank（同順位は平均ランクを取る実装）、factor_summary（count/mean/std/min/max/median）を提供。
    - 外部依存を避け、標準ライブラリのみで実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（api_key）で、環境変数 OPENAI_API_KEY のみの依存を避けてテスト性を向上。
- 環境変数の自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 実装上の注意 / 既知の設計意図
- ルックアヘッドバイアス対策として、内部処理は datetime.today()/date.today() を直接参照しない設計になっている（すべて caller が target_date を渡す方式）。
- OpenAI 呼び出しでの障害はフェイルセーフに処理し、可能な限りゼロ相当値（中立）にフォールバックしてパイプライン全体の継続を優先する設計。
- DuckDB のバージョン互換性（executemany に空リストを渡せない等）に配慮した実装上の防御が入っている。
- テスト容易性を意識して、外部 API 呼び出し箇所はモック差し替えができるよう抽象化されている（例: _call_openai_api を patch 可能）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（注文ロジック、発注安全ガード、実行モニタリング）
- ai モデルのプロンプト最適化、ログ・メトリクスの拡張
- ETL の品質チェック強化および自動修正ルールの導入

（必要であれば、この CHANGELOG をリリースに合わせて更新します）