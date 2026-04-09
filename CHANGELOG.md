Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
意味のある互換性のあるバージョン番号は SemVer を使用します。

[Unreleased]
------------

0.1.0 - 2026-04-09
------------------

Added
- 初回リリース。kabusys パッケージ全体を追加。
- 基本情報:
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ説明: 日本株自動売買システムのコアユーティリティ群

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env パーサは export 構文、クォート、エスケープ、インラインコメント処理に対応。
  - OS 環境変数を保護する protected 機構、.env.local による上書き処理。
  - 必須キー取得の _require と、各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_* 等）。
  - DB パスや paper trading 設定、監視用閾値、環境モード（development/paper_trading/live）・ログレベル検証等をサポート。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: buy シグナルのスコアで上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全て 0 の場合等金額にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションの時価から上限超過セクターをブロック。unknown セクターは除外しない設計。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）とフォールバック挙動（未知レジームは警告して 1.0）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の各割当方式に対応。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的コスト見積り。残差分の配分ロジックを実装。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（MA200 の行数不足時は None）を DuckDB の prices_daily から計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算（EPS=0 または欠損時は None）。
    - DuckDB を利用した効率的なウィンドウ関数クエリ設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一 SQL で取得。horizons 引数の検証あり（1-252 営業日）。
    - calc_ic: スピアマンランク相関（IC）を実装。欠損や同順位処理に対応し、有効レコード数が 3 未満なら None。
    - rank: 同順位は平均ランクにする実装（丸め誤差対策で round(v,12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- AI 関連 (src/kabusys/ai/)
  - news_nlp:
    - raw_news → OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ保存。
    - ニュースウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して扱う calc_news_window）。
    - 記事集約（銘柄ごと最大記事数・文字数でトリム）、20 銘柄バッチ送信、JSON Mode を利用した厳格な出力検証。
    - API エラー（429/接続/タイムアウト/5xx）に対する指数バックオフリトライ、その他失敗はスキップ（フェイルセーフ）。
    - レスポンスバリデーションとスコアの ±1.0 クリップ、部分書き込み（対象コードのみ DELETE→INSERT）で部分失敗の影響を最小化。
    - テストフレンドリー: _call_openai_api を patch して差し替え可能。
  - regime_detector:
    - ETF 1321 の MA200 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - _calc_ma200_ratio: target_date 未満のデータのみ使用しルックアヘッドを防止。データ不足時は中立フォールバック。
    - マクロニュース取得はキーワード検索と上限数（タイトル抽出）。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 生成したレジームは market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - news_nlp と内部でプロンプト実装を分離し、モジュール間のプライベート関数共有を避ける設計。
  - ai パッケージは score_news をエクスポート。

- 監視（Monitoring DB） (src/kabusys/monitoring/monitoring_db.py)
  - SQLite ベースの永続化層を提供。system_status / trade_logs / positions / risk_logs etc. のテーブルとインデックスを冪等に作成する init_monitoring_db。
  - ビジネスロジック非保持（読み書きのみ）。

- モジュールのエクスポート整理
  - kabusys.portfolio, kabusys.research, kabusys.ai の __all__ にて主要関数を明示的に公開。

Security
- 環境変数のパースおよび API キー取り扱いに注意。OpenAI API キーは引数または環境変数 OPENAI_API_KEY で渡す（未設定時は ValueError を送出）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - research / ai / regime 判定など全ての時系列ロジックは target_date を明示的に受け取り、datetime.today() を参照しない設計。
  - prices_daily のクエリも target_date 未満 / equal の扱いを明示している箇所あり。
- フォールバック / フェイルセーフ:
  - API 呼び出し失敗時は極力 0.0（中立）やスキップで処理を継続し、全面停止しない挙動。
  - DB 書き込みはトランザクションで保護し、失敗時は ROLLBACK を実施。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数を patch することで外部 API 呼び出しをモックできる設計。
- 外部依存:
  - DuckDB をデータ処理に使用。SQLite は監視ログ用に使用。
  - OpenAI Python SDK に依存（gpt-4o-mini を利用想定）。

Breaking Changes
- （初回リリースのため該当なし）

参考
- 各モジュールの詳細はソースコード内の docstring およびコメントを参照してください（StrategyModel.md / PortfolioConstruction.md 等を参照する記述あり）。

---