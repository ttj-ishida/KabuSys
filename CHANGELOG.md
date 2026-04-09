# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
リリース: 初期公開 (version 0.1.0)

### 追加 (Added)
- パッケージ初期構成を追加
  - パッケージ名: kabusys、トップレベル __version__ = 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境変数・設定管理
  - .env ファイルまたは環境変数から設定を安全に読み込む `kabusys.config` を実装
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動ロード
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応
    - 上書き制御（override / protected）により OS 環境変数を保護して読み込み
  - `Settings` クラスで各種設定をプロパティとして提供
    - J-Quants / kabu ステーション / LINE / DB パス などの設定プロパティ
    - `paper_fill_mode` のバリデーション（instant/partial/never/reject）
    - 環境（development/paper_trading/live）とログレベル（DEBUG..CRITICAL）のバリデーション
    - パスは Path オブジェクトとして展開（expanduser）

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング: `score_news(conn, target_date, api_key=None)`
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）にバッチ送信してセンチメントを算出
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたり記事数・文字数上限対応
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ＆リトライ、パース失敗・検証失敗時は該当チャンクをスキップ
    - レスポンス検証ロジック（JSON 抽出、results フォーマット検査、未知コード除外、数値チェック、スコアの ±1 クリップ）
    - DB 書き込みは部分失敗に備え、取得したコードのみ削除→挿入（冪等）
    - テスト用に API 呼び出し関数をパッチ可能（unittest.mock.patch で差替え）
    - ニュース対象ウィンドウ定義（JST 基準）を提供: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）
  - 市場レジーム判定: `score_regime(conn, target_date, api_key=None)`
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を判定
    - ma200_ratio 計算、マクロ記事抽出、OpenAI によるマクロスコア取得、合成スコアの閾値判定を実装
    - OpenAI 呼び出しに対するリトライ、API 失敗時は macro_sentiment=0.0 のフォールバック
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト用に API 呼び出し関数をパッチ可能（news_nlp とは独立に実装）

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理: `calendar_management`
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job(conn, lookahead_days=90)`
    - 営業日判定ユーティリティ: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した振る舞い
    - 最大探索範囲やバックフィル、健全性チェックを設計に組込み（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）
    - J-Quants クライアントとの連携（fetch/save）を想定
  - ETL パイプライン基盤: `pipeline.ETLResult` と周辺設計
    - `ETLResult` dataclass を公開し、ETL の取得数/保存数、品質問題一覧、エラー一覧を集約できる
    - ETL の設計指針（差分取得、バックフィル、品質チェックの扱い）を実装に反映
  - ETL 公開インターフェース `data.etl` で ETLResult を再エクスポート

- リサーチ/ファクター計算 (kabusys.research)
  - ファクター計算モジュール `factor_research` を実装
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）
    - Volatility/Liquidity: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio
    - Value: PER（price / EPS）、ROE（raw_financials の最新レコードを結合）
    - DuckDB を活用した SQL ベースの計算、データ不足時の None ハンドリング
  - 特徴量探索モジュール `feature_exploration`
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=[1,5,21])`（LEAD を使用）
    - IC（Information Coefficient）計算: `calc_ic`（Spearman 相関相当をランクで算出）
    - ランク変換ユーティリティ `rank`
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）
    - 外部依存を避けた純粋 Python 実装を意識

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を使用し、未設定時は明示的に ValueError を発生させることで誤動作を防止

### 注意事項 / 設計上の挙動
- ルックアヘッドバイアス対策: 全てのスコアリング／ファクター計算関数は内部で datetime.today()/date.today() を参照せず、必ず引数の target_date を基準に処理します。
- フェイルセーフ: OpenAI API の失敗やパース失敗は致命的例外にせず、該当部分を 0 や空でフォールバックする設計（部分失敗耐性）。
- テスト性: OpenAI 呼び出し部分は内部関数を patch できるように分離しており、ユニットテストで差し替え可能。
- DuckDB 互換性: 一部 executemany に関する注意（空リスト渡し不可）等を考慮した実装になっています。
- デフォルトパス・値:
  - duckdb: data/kabusys.duckdb
  - sqlite (monitoring): data/monitoring.db
  - paper_trading sqlite: data/paper_trading.db
  - pid / kill flag 等のパスも設定可能

### 既知の制約 / 今後の改善候補
- news_nlp / regime_detector は gpt-4o-mini の JSON Mode に依存しているためモデル変更時はプロンプト・レスポンス検証ロジックの見直しが必要
- ETL / calendar 更新で J-Quants クライアント実装（fetch/save）の堅牢化と単体テストの充実化が望ましい
- 一部 SQL クエリは DuckDB のバージョン差異に依存する可能性があるため、CI での DuckDB バージョンテストを推奨

---

著者: kabusys 開発チーム（コードベースから推測して記載）
（本 CHANGELOG は提示されたコード内容に基づき生成された推定の変更履歴です。実際のコミット履歴・リリースノートと差異がある場合があります。）