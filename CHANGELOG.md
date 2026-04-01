# CHANGELOG

すべての重要な変更点を追跡します。フォーマットは Keep a Changelog に準拠しています。  

なお、この CHANGELOG は提供されたコードベースから実装内容を推測して作成した初期リリース向けのまとめです。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__、バージョン: 0.1.0、公開モジュール一覧: data, strategy, execution, monitoring）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - .env パーサは export プレフィックス、クォート文字、エスケープ、コメントなどに対応。
    - 読み込み時に OS 環境変数を保護するための protected キー概念を導入。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得可能に:
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）/監視閾値（CPU/MEM/DISK）/ログレベル/環境種別（development/paper_trading/live）等。
    - 必須環境変数は未設定時に ValueError を送出する `_require` を実装。
- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを準備。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大バッチサイズ 20 銘柄）。
    - JSON Mode を利用した厳密な JSON レスポンス期待、応答のバリデーションと数値クリップ（±1.0）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - 結果は ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT の置換処理）。
    - テスト容易性: OpenAI 呼び出し部分はモジュール内関数をパッチ可能に設計（unittest.mock.patch など）。
    - ニュースウィンドウ計算ユーティリティ（calc_news_window）を実装（JST ベースの前日 15:00 ～ 当日 08:30）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を統合して日次レジーム（bull/neutral/bear）を判定。
    - DuckDB からの prices_daily / raw_news 参照、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント算出、スコア合成と market_regime への冪等書き込みを実装。
    - API エラーやパース失敗に対するフェイルセーフ（macro_sentiment=0.0）とリトライロジックを実装。
- データ基盤（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを実装。
    - DB にデータがない場合は曜日（平日）ベースでのフォールバックを行う設計。
    - calendar_update_job を実装し、J-Quants からカレンダーを差分取得して冪等保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン（pipeline）および公開インターフェース（etl）
    - ETLResult dataclass を実装し、ETL の取得件数・保存件数・品質問題・エラー概要を集約。
    - 差分取得・保存・品質チェックに関する設計（バックフィル、事後修正吸収、idempotent 保存）を反映。
- リサーチ機能（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー系の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（不足時は None）を計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを参照して PER / ROE を計算（EPS が 0 または欠損時は None）。
    - SQL ウィンドウ関数を活用し、DuckDB 上で完結して計算。
  - feature_exploration: 将来リターン計算 / IC（Information Coefficient） / 統計サマリー / ランキングユーティリティを実装。
    - calc_forward_returns: 指定ホライズン先（営業日ベース）の将来リターンを一括で取得。
    - calc_ic: スピアマンランク相関による IC を実装（有効レコード 3 件未満は None）。
    - rank, factor_summary を提供（同順位の平均ランク処理、基本統計量算出）。
  - すべてのリサーチ処理は DuckDB を入力に取り外部 API に依存しない設計。
- テスト性 / 安全性向上
  - ルックアヘッドバイアス防止のため、各モジュールは date.today() / datetime.today() を直接参照しない設計（関数呼び出し側から target_date を渡す）。
  - OpenAI 呼び出し部は明示的に内部関数として定義しており、テストで差し替え可能。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の明示的使用）。
  - エラー時のフォールバック動作（API エラー時のスコア 0.0 やスキップ）を明確に実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 機密情報（API キー等）は Settings 経由で環境変数から取得する設計。自動ロード処理で OS 環境変数を上書きしない保護機能を備えています。

Notes / 備考
- OpenAI（gpt-4o-mini）連携箇所は外部 API に依存するため、実行環境には適切な API キーとネットワークが必要です。テスト環境では内部の API 呼び出し関数をモックすることを推奨します。
- DuckDB を利用する SQL 実装はバージョン差分に注意（コード内に DuckDB バージョン依存の回避策が含まれます）。
- .env パーサは多くの実用ケース（export 形式、クォート・エスケープ・インラインコメント）に対応していますが、極端な非標準書式の .env は想定外の挙動になる可能性があります。

------------------------------------------------------------------------------------------------
（以降のリリースでは Unreleased → 次バージョンへ移動し、変更点を追記してください）