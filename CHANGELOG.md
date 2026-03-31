Keep a Changelog
=================
すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

注記
----
- 日付はリリース日を示します（ここではコードから推測した初回リリース日を使用しています）。
- 記載はコードベースの内容から推測して作成しています。実際の履歴やコミットメッセージとは異なる可能性があります。

Unreleased
----------
（今後の変更をここに記載）

[0.1.0] - 2026-03-31
--------------------
Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。__version__ = 0.1.0。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - 環境変数読み込み・管理モジュールを追加（kabusys.config）。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）により、.env / .env.local を自動読み込み。
  - .env パーサの実装：コメント、export プレフィックス、クォートとバックスラッシュによるエスケープ、インラインコメント等に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等のプロパティを提供。未設定の必須環境変数は ValueError を送出。

- AI（自然言語処理 / レジーム判定）
  - ニュースセンチメント解析モジュールを追加（kabusys.ai.news_nlp）。
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI gpt-4o-mini（JSON mode）でスコアリング。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事・文字数上限を導入（記事数最大 10、文字数 3,000 文字）。
    - リトライ戦略（429/ネットワークエラー/タイムアウト/5xx）を実装し、指数バックオフで再試行。
    - レスポンス検証（JSON パース、results 配列、code/score の検証、数値クリップ ±1.0）。部分成功時は既存スコアを保護するため対象コードのみ DELETE → INSERT で上書き。
    - テスト容易性を考慮し、API 呼び出し部分を関数化してモック差し替え可能。
  - 市場レジーム判定モジュールを追加（kabusys.ai.regime_detector）。
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定。
    - マクロニュースはマクロキーワードリストで抽出し、OpenAI によりセンチメントを JSON で取得。
    - lookahead バイアス回避の設計（target_date 未満のデータのみを使用、datetime.today() を参照しない）。
    - API エラーやパース失敗は macro_sentiment=0.0 のフェイルセーフで継続。
    - 市場レジーム結果は market_regime テーブルに冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK）。

- データプラットフォーム
  - ETL パイプライン（kabusys.data.pipeline）を追加。
    - 差分取得、バックフィル、品質チェックの枠組みを定義。
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどのユーティリティ実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）。
    - JPX カレンダー差分取得ジョブ（calendar_update_job）実装：J-Quants から取得 → market_calendar に冪等保存。
    - 営業日判定ユーティリティ群を実装：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得時の曜日ベースフォールバックや、DB の不整合（NULL 値）への対処（ログ出力）を実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) など安全策を導入。
  - jquants_client との連携点を設計（fetch/save 関数を利用する前提の実装箇所を用意）。

- リサーチ / ファクター
  - ファクター計算モジュール群を追加（kabusys.research）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務を取得して PER、ROE を計算（EPS 欠損・0 の場合は None）。
    - calc_forward_returns: 任意ホライズンの将来リターン取得（デフォルト [1,5,21]）。horizons の検証あり。
    - calc_ic / rank: ファクターと将来リターンのランク相関（Spearman ρ）を計算するユーティリティを実装。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）計算ユーティリティ。
  - 実装方針として DuckDB と標準ライブラリのみを使用し、外部依存を抑制。

- ロギング・堅牢性
  - 多数の箇所で詳細なログメッセージを実装（info/debug/warning/exception）。
  - API 呼び出しのリトライ・フェイルセーフや、DB 書き込みのトランザクション管理（COMMIT/ROLLBACK）を適用。
  - ルックアヘッドバイアス回避（日時の扱いを明示的に制御）を設計方針として徹底。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数で API キーを扱う設計。必須変数未設定時は明確な例外を投げることで誤った運用を防止。

Notes / 注意点
- OpenAI SDK（OpenAI クライアント）に依存する箇所があるため、環境に応じた API キー設定とレート制限対策が必要。
- DuckDB の executemany に空リストを渡せない制約に対するワークアラウンド（条件付き executemany）を実装。
- news_nlp と regime_detector の OpenAI 呼び出しはそれぞれ別実装の private 関数になっており、意図的にモジュール間で共有していない（独立性を維持）。
- .env パーサは Bash 風の記法をある程度サポートするが、すべてのシェル文法に対応するわけではないことに注意。

今後の候補タスク（提案）
- strategy / execution / monitoring モジュールの実装／統合テストの追加。
- J-Quants / kabu クライアント実体の注入・モック化を容易にするためのインターフェース強化。
- OpenAI レスポンスの更なる堅牢化（スキーマ検証ライブラリ導入等）。
- ドキュメント（使用例、環境構築、DB スキーマ）および CI テストの整備。