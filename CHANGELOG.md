# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお本リリースは初期公開相当（v0.1.0）であり、主要なモジュール実装と設計方針が含まれます。

## [0.1.0] - 2026-03-31

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 主要サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（配布後も動作するよう設計）。
  - .env パース処理の実装:
    - export プレフィックス対応、単一/二重クォート、バックスラッシュエスケープ、行内コメント処理などを考慮した堅牢なパーサ。
  - Settings クラスを提供（プロパティ経由で宣言的に設定を取得）。
    - J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境モード（development/paper_trading/live）などを取得するプロパティを実装。
    - 必須変数未設定時は ValueError を送出する _require 実装。
    - 環境値の検証（有効な env 値・LOG_LEVEL 値のチェック）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメント分析して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用（calc_news_window 実装）。
    - バッチ処理: 最大 20 銘柄/コール（_BATCH_SIZE）、1 銘柄あたり記事は最新10件・3000文字でトリム。
    - 再試行ポリシー: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（設定可能な上限）。
    - レスポンス検証: JSON パース、results キー/型チェック、未知コード無視、スコア数値検証、±1.0 にクリップ。
    - 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）し、DuckDB の executemany の空リスト制約に配慮。
    - テスト容易性: _call_openai_api はパッチ可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロ記事抽出はマクロキーワード群でフィルタ（キーワードリスト実装）。
    - LLM 呼び出し: gpt-4o-mini の JSON モード、リトライ・エラー処理を実装。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - スコア合成・閾値に基づくラベル付け、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - lookahead バイアス対策: date.today() を参照せず、target_date 未満のデータのみを使用。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を提供（取得件数、保存件数、品質問題リスト、エラーリスト等を含む）。
    - 差分更新・バックフィル・品質チェックを想定した設計（バックフィルデフォルト・品質問題は収集して継続）。
    - DuckDB 上の最大日付取得、テーブル存在チェック等のユーティリティを実装。
  - ETL 公開インターフェース（kabusys.data.etl）
    - ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - lookahead / backfill / 健全性チェック（未来日付の異常検知）を実装。
    - 営業日判定・次/前営業日取得・期間内営業日リスト取得・SQ日判定などのユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日扱い）。DB が一部しか登録されていない場合でも一貫性を保つ設計。
    - 最大探索範囲（_MAX_SEARCH_DAYS）で無限ループを防止。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB SQL で計算する関数群を実装。
    - 欠損やデータ不足時の扱い（None を返す）を明確化。
    - 計算範囲バッファやウィンドウサイズ等の定数を定義。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic）算出、ランク変換（rank）、カラムサマリ（factor_summary）を実装。
    - 外部依存を避け、標準ライブラリと DuckDB で動作する設計。
  - research パッケージ __all__ を通じて主要関数を公開（zscore_normalize は data.stats からの再利用）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能（api_key 引数）で、環境変数 OPENAI_API_KEY を直接参照する実装も提供。  
  - 必須未設定時は明確な ValueError を返す。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策が各種処理（news scoring / regime scoring / factor 計算）で一貫して適用されている（datetime.today()/date.today() を内部で参照しない、クエリは target_date 未満/以前の条件を厳守）。
- OpenAI 呼び出し部分はテスト用に差し替え可能（内部 _call_openai_api を patch する想定）。
- DuckDB の互換性・制約（executemany の空リスト不可など）に配慮した実装。
- 冪等性を考慮した DB 書き込み（対象を限定した DELETE → INSERT、BEGIN/COMMIT/ROLLBACK 管理）を行っている。
- ロギングを多用し、警告・情報・例外発生箇所を明示。

---

将来のリリースでは次のような追記を予定しています:
- strategy / execution / monitoring の具体的戦略実装および発注ロジック
- テストカバレッジ向上（ユニット・統合テスト）
- Docker / CI 設定、デプロイ手順のドキュメント化
- パフォーマンス最適化および大規模データ処理向けチューニング

もし CHANGELOG に追記してほしい点（例えばより詳細な内部設計メモや追加モジュールの記載）があれば教えてください。