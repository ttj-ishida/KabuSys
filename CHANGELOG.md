CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
バージョンや日付は、今回のコードベース（src/kabusys 以下）の状態から推測して作成しています。

Unreleased
----------
今後の予定（コードのコメントや未実装箇所から推測）
- ユニットテストの追加（特に OpenAI 呼び出し・DuckDB 操作部分のモックを含むテスト）
- ドキュメント強化（API 使用例、DB スキーマ、運用手順）
- CLI / 実行ユーティリティの追加（ETL やカレンダー更新、AI スコアリングのジョブ化）
- 監視・実行モジュールの実装補完（パッケージの __all__ に含まれる monitoring / execution の整備）
- パイプライン実装の補完・リファクタ（パイプラインの一部に不完全な箇所が見られるため）

[0.1.0] - 2026-03-31
--------------------
初回公開リリース（コードベースのスナップショットから推測）

Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョン設定を追加（__version__ = "0.1.0"）。
  - パッケージの主要サブモジュールを __all__ で公開: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出: .git or pyproject.toml を基準）。
  - .env ファイルの柔軟なパース実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
    - クォート無しのコメント判定（'#' の直前が空白/タブのときのみコメント扱い）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数保護（読み込み時に既存の os.environ キーを保護する仕組み）。
  - Settings クラスを公開し、アプリ設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境（development/paper_trading/live）など。
  - 必須環境変数未設定時に明確なエラーメッセージを出す _require 実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）モジュールを追加。
  - news_nlp:
    - タイムウィンドウ計算（calc_news_window）: JST ベースで前日 15:00 ～ 当日 08:30 を対象（内部は UTC naive datetime を使用）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1銘柄あたり記事数・文字数のトリム付き）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄/チャンク）、JSON Mode を利用した厳密パース想定。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。非再試行系エラーはスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーション処理（JSON 復元、results 配列 → code/score の検証、スコアを ±1.0 にクリップ）。
    - DuckDB への冪等書き込みロジック（取得済みコードのみ DELETE → INSERT）と DuckDB executemany の空リスト対策。
  - regime_detector:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、news_nlp を用いたマクロセンチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - prices_daily から target_date 未満のデータのみを使いルックアヘッドバイアスを回避。
    - OpenAI 呼び出しは専用実装で分離（モジュール結合を避ける）。
    - API 呼び出しの再試行/バックオフ、パース失敗や API エラー時は macro_sentiment=0.0 にフォールバック。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK 処理のログ）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - Momentum: mom_1m/mom_3m/mom_6m、ma200 偏差（ma200_dev）を DuckDB 上で計算。必要期間が足りない場合は None を返す。
    - Volatility: 20日 ATR（true range の扱いに注意）、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から前回報告値を取得して PER、ROE を計算（EPS が無効な場合は None）。
    - 設計方針として DuckDB の SQL + Python による完結した処理（外部 API へはアクセスしない）を採用。
  - feature_exploration:
    - 将来リターン（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - IC 計算（calc_ic）: スピアマンランク相関（ランク化は平均ランク、ties の扱いに配慮）。
    - rank / factor_summary: ランク付けユーティリティと基本統計量サマリを提供。
  - research パッケージは主要関数を __all__ でエクスポート。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを元に営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除外）をフォールバックとして扱う。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等（再フェッチ・バックフィル・健全性チェックを含む）で更新。
  - pipeline / etl:
    - ETLResult データクラスを公開して ETL 実行結果を構造化（品質チェックの結果やエラー情報を含む）。
    - ETL パイプラインの設計方針（差分更新、backfill、品質チェックは Fail-Fast とせず呼び出し元が判断）を反映。
    - jquants_client / quality モジュールを利用する想定の実装を整備。
  - etl モジュールは ETLResult を再エクスポート。

Changed
- （初回リリースのため "Changed" 相当の過去変更は無し。実装上の設計決定をドキュメントとして反映。）

Fixed
- （初回リリースのため明示的な修正履歴は無し。ただし各モジュールで例外処理・フォールバック・冪等性を念頭に実装されている点を注記。）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決する。必須未設定時は ValueError を発生させ明示的に通知。
- .env 自動ロードは環境変数で無効化可能（テスト環境・CI での安全性確保）。

Notes / 設計上の重要ポイント（リリース概要）
- ルックアヘッドバイアス回避: AI スコアリング / レジーム判定 / ファクター計算は内部で date.today()/datetime.today() を参照せず、すべて target_date ベースで処理する設計。
- フェイルセーフ: OpenAI や外部 API の障害時はプロセス全体を停止せず、局所的にゼロやスキップで継続できるよう実装（ログは詳細に出力）。
- 冪等性: DB 書き込みは基本的に上書き（DELETE→INSERT / ON CONFLICT）で冪等に保つ設計。
- テスト容易性: OpenAI 呼び出し部分はモジュール内で分離され、単体テスト時に patch/mocking しやすい作りになっている。
- DuckDB を一次データレイヤとして使用し、SQL と Python を組み合わせた処理を行う方針。

Contributors
- 本 CHANGELOG はコード内のコメント・実装から推測して作成しました。実際のコミット履歴が存在する場合は、今後のリリースで正式な差分ログ（コミット単位）に置き換えてください。