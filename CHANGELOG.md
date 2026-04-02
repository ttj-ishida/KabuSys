# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
現在のバージョン: 0.1.0（初期リリース）

最新更新日: 2026-04-02

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-02

Added
- パッケージ初期リリース "KabuSys" を追加（__version__ = 0.1.0）。
- パッケージ構成
  - kabusys パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ として公開。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、CWD に依存しない自動 .env ロードを実現。
  - 複数の .env 読み込み順序を実装（OS環境変数 > .env.local > .env）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env のパース機能を強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメントの適切処理（クォートあり/なしの差異を考慮）
  - 既存 OS 環境変数を保護する protected キーセットを導入（.env 上書き時の安全対策）。
  - Settings クラスでアプリケーション設定をプロパティ化：
    - J-Quants / kabu API / Slack / データベースパス / 監視閾値 / env/log level 等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値チェック）。
    - Path 型を返すプロパティ（duckdb_path 等）は expanduser により ~ を解釈。
- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュールを実装（score_news）：
    - タイムウィンドウ算出（前日15:00 JST ～ 当日08:30 JST に対応、UTC変換済み）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1銘柄あたり最大件数・文字数でトリム）。
    - gpt-4o-mini（OpenAI JSON mode）へバッチ送信（最大バッチサイズ 20 銘柄）。
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配下の code/score 検証、数値変換、既知コード照合）。
    - スコアは ±1.0 にクリップし、取得済み銘柄のみ ai_scores テーブルへ置換（DELETE→INSERT、部分失敗時に既存スコア保護）。
    - API キー注入（api_key 引数または OPENAI_API_KEY 環境変数）。
    - フェイルセーフ設計（API 失敗時は該当チャンクをスキップして継続）。
  - regime_detector モジュールを実装（score_regime）：
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して市場レジーム判定（bull / neutral / bear）。
    - ma200 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - raw_news からマクロキーワードで記事タイトルを抽出（最大件数制限）。
    - OpenAI 呼び出しは専用関数を通じて実行、retry ロジック・ステータスコード判定を実装。API 失敗時は macro_sentiment=0.0 をフォールバック。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - ルックアヘッドバイアス対策（datetime.today()/date.today() 参照を避ける設計）。
- Research（研究）モジュール（kabusys.research）
  - factor_research モジュールを実装：
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時ハンドリング）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（欠損値処理）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 の扱い）。
    - DuckDB を利用した SQL ベースの実装で外部 API に依存しない設計。
  - feature_exploration モジュールを実装：
    - calc_forward_returns: 任意ホライズンの将来リターン（営業日ベース）を一括取得する効率的クエリ。
    - calc_ic: スピアマンのランク相関（IC）を実装（欠損・同値処理）。
    - rank / factor_summary: ランク化ユーティリティと基本統計量サマリーを実装。
    - pandas 等に依存しない純標準ライブラリでの実装。
- Data（データ基盤）モジュール（kabusys.data）
  - calendar_management を実装：
    - market_calendar を利用した営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB データ優先、未登録日は曜日ベースのフォールバック実装。
    - calendar_update_job: J-Quants API 経由で差分取得→冪等保存（バックフィル・健全性チェックを含む）。
  - pipeline / etl / ETLResult（kabusys.data.pipeline / etl）を実装：
    - ETLResult データクラスを定義し公開（etl モジュールで再エクスポート）。
    - ETL ワークフロー設計方針（差分更新、バックフィル、品質チェックの概念）を反映。
    - jquants_client, quality モジュールとの連携ポイントを設け、ID トークン注入でテスト容易性を確保。
- テスト容易性を考慮した設計
  - OpenAI 呼び出し箇所に対して unittest.mock.patch による差し替えが可能な内部関数を用意。
  - API キーは引数注入と環境変数の両方に対応（テスト時の依存注入を想定）。

Security
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを防止。

Notes / Design choices
- ルックアヘッドバイアス対策を徹底（各 AI/研究モジュールで date.today() を参照しない）。
- DuckDB を中心とした SQL 処理でデータ処理の再現性・パフォーマンスを重視。
- AI（OpenAI）呼び出しは JSON mode を前提としたレスポンスパーシングと堅牢なバリデーションを実装。

Known issues / Limitations
- data/pipeline.py の末尾付近に実装ミスまたは切り欠け（_get_max_date 内の return に不自然な痕跡）が認められます。初期実装段階の不完全箇所として今後の修正を予定しています。
- strategy, execution, monitoring 等の一部公開モジュールはパッケージトップで宣言されていますが、本リリース中のコードベースに含まれる実装範囲は限定的です。運用（実際の発注）に関する機能は別途実装・レビューが必要です。
- OpenAI の利用は gpt-4o-mini を前提としているため、API 仕様変更やモデル提供状況に応じて調整が必要となる可能性があります。
- DuckDB のバージョン依存（executemany の空リストの扱い等）を考慮した実装がされているため、使用する DuckDB のバージョンで挙動確認を行ってください。

---

今後の予定（次バージョン候補）
- pipeline の未完了・境界ケースの修正
- strategy / execution の注文ロジックおよび監視（monitoring）機能の実装拡充
- テストカバレッジ追加（特に AI 呼び出しのエラーパス、DB 書込ロールバックのケース）
- ドキュメント充実（使用方法、デプロイ手順、環境変数サンプル .env.example の整備）

（この CHANGELOG はコードの実装内容から推測して記載しています。実際の変更履歴やリリースノートはリポジトリ管理者の公式情報を優先してください。）