# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。

### Added
- パッケージの基本構成
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開モジュール群: data / research / ai / monitoring / strategy / execution を想定したパッケージ構成を用意。

- 環境設定管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を読み込む自動ローダ実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に __file__ から上位ディレクトリを探索（CWD 非依存）。
  - .env パーサ実装（export 形式対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - 自動ロード優先度: OS環境 > .env.local（上書き） > .env（未設定のみセット）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを公開（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境・ログレベル等のプロパティを提供）。
  - 一部必須環境変数未設定時に ValueError を送出する保護（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

- ニュースNLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメント分析。
  - ニュース収集ウィンドウ計算（JST基準）と raw_news / news_symbols の集約ロジック実装。
  - バッチ処理（最大20銘柄/リクエスト）、1銘柄あたりの記事数・文字数上限（デフォルト: 10記事・3000文字）。
  - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライ、その他はスキップして継続。
  - JSON Mode 応答の頑強なパース（先頭/末尾余分テキスト混入時の復元処理含む）。
  - スコアのバリデーション（requested_codes に基づくフィルタ、数値性・有限性チェック、±1.0 クリップ）。
  - DuckDB に対する idempotent な書き込み（DELETE→INSERT、executemany 空リスト回避の考慮）。
  - パブリック関数: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム判定（bull/neutral/bear）。
  - prices_daily からの MA 計算（ルックアヘッド防止: date < target_date を採用）と raw_news からのマクロ記事抽出。
  - OpenAI 呼び出しのリトライ・エラー処理（API失敗時は macro_sentiment を 0.0 にフォールバック）。
  - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）。
  - パブリック関数: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データ基盤ユーティリティ（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新ロジック（J-Quants から差分取得、ON CONFLICT 相当で保存）。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。探索上限の設定による安全性確保。
    - calendar_update_job(conn, lookahead_days=90) — 取得・保存した件数を返す。

  - ETL パイプライン（pipeline）
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラー一覧などを保持）。
    - 差分取得・バックフィル・品質チェックの考え方を実装（実装は ETLResult を中心に公開）。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ/ファクター（kabusys.research）
  - factor_research:
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）。
    - ボラティリティ/流動性: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率。
    - バリュー: PER（株価/EPS）、ROE（raw_financials の最新レコード参照）。
    - DuckDB を用いた SQL ベースの効率的実装。データ不足時は None を返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の fwd_* 計算、引数検証。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関（ties の平均ランク処理）。
    - 統計サマリー（factor_summary）とランク化ユーティリティ（rank）。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB のみで実装。

### Changed
- 設計方針の明示
  - ルックアヘッドバイアス防止のため、各種スコア計算で datetime.today() / date.today() を直接参照しない方針を採用。明示的に target_date を引数として渡す設計に統一。
  - OpenAI 呼び出しや DB 書き込みはフェイルセーフ（API障害時は無理に停止せず中立値やスキップで継続）を優先。

### Fixed
- DuckDB 互換性と安全性
  - executemany に空リストを渡すと失敗する環境向けに、空チェックを追加して不要な呼び出しを防止。
  - market_regime / ai_scores への書き込みでトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、エラー時に ROLLBACK を試行。ROLLBACK 自体の失敗は警告で記録。

- OpenAI 応答の堅牢化
  - JSON Mode 使用時でも前後に余計なテキストが混ざるケースを想定して最外側の { } を抽出してパースする復元処理を追加。
  - API エラーの種類（RateLimit / Connection / Timeout / APIError）に応じたリトライ・フォールバック処理を追加。

### Security
- API キー解決に関する明確化
  - OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY を優先的に使用。未設定時は ValueError を投げて明示的に通知。

### Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を想定（JSON Mode を利用して厳密な JSON レスポンスを期待）。
- 各モジュールでロギングを適切に配置（info/debug/warning/exception）して運用時の観測性を確保。
- 多くの設計上の判断（例: 部分失敗時に既存データを保持するためのコード絞込 DELETE → INSERT の採用、API失敗時の中立スコアフォールバックなど）は本番運用を想定した安全重視の方針に基づく。

---

（補足）本 CHANGELOG は現行コードベースの実装内容から推測して作成しています。将来のリリースでは実際の変更履歴に合わせて適宜更新してください。