# CHANGELOG

すべての notable な変更はこのファイルに記録します。本ファイルは "Keep a Changelog" の形式に準拠します。  

最新リリース
- [Unreleased]

履歴
- [0.1.0] - 2026-03-20
  - Added
    - 初回リリース: KabuSys v0.1.0 を追加。
    - パッケージ構成:
      - パブリックモジュール: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（__all__ に公開）。
      - バージョン情報: __version__ = "0.1.0" を追加。
    - 環境設定管理 (kabusys.config):
      - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - export KEY=val 形式やクォート／エスケープ／行末コメントなどを考慮した .env パーサ実装。
      - settings オブジェクトを提供。必須値を取得する _require() と各種設定プロパティを用意（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
      - 環境変数の妥当性チェック（KABUSYS_ENV、LOG_LEVEL の許容値検証）。
    - データ取得・保存 (kabusys.data):
      - J-Quants API クライアント (jquants_client):
        - ページネーション対応の fetch_* 関数（株価日足、財務、マーケットカレンダー）。
        - 固定間隔のレートリミッタ（120 req/min）を実装。
        - リトライ（指数バックオフ、最大3回）、429 の Retry-After の考慮、401 受信時のトークン自動リフレッシュ（1回）を実装。
        - データを DuckDB に冪等保存する save_* 関数（ON CONFLICT DO UPDATE）を提供（raw_prices, raw_financials, market_calendar）。
        - 型変換ユーティリティ (_to_float/_to_int) を実装し、不正値を安全に扱う。
      - ニュース収集 (news_collector):
        - RSS フィード取得、URL 正規化（トラッキングパラメータ削除、ソート、フラグメント除去）、記事ID を SHA-256 ベースで生成して冪等性を担保。
        - defusedxml を用いた安全な XML パース、受信サイズ制限、SSRF 対策などセキュリティ上の配慮を実装。
        - raw_news テーブルへのバルク保存（チャンク処理、INSERT RETURNING を想定）を想定した実装方針。
    - リサーチ/ファクター計算 (kabusys.research):
      - factor_research: モメンタム、ボラティリティ、バリュー（PER/ROE 等）を DuckDB の prices_daily / raw_financials を参照して計算する関数群（calc_momentum, calc_volatility, calc_value）。
      - feature_exploration: 将来リターン計算（複数ホライズン対応 calc_forward_returns）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
      - zscore_normalize は kabusys.data.stats（外部）を利用する形で統合可能にしている（reexport）。
    - 戦略モジュール (kabusys.strategy):
      - feature_engineering.build_features:
        - research 側で算出した raw ファクター群をマージし、ユニバースフィルタ（最低株価・平均売買代金）適用、Z スコア正規化（対象列を指定、±3 でクリップ）し features テーブルへ日付単位で置換（冪等）。
        - DuckDB トランザクション（BEGIN/COMMIT/ROLLBACK）による原子性を確保。
      - signal_generator.generate_signals:
        - features と ai_scores を統合し、複数のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出。
        - デフォルト重み・閾値を用意し、ユーザ指定重みは検証／正規化して合計が 1.0 にスケール。
        - Bear レジーム判定（ai_scores の regime_score の平均が負）により BUY を抑制。
        - BUY（threshold 超）・SELL（ストップロスやスコア低下）を生成し、signals テーブルへ日付単位で置換（冪等）。
        - SELL 優先ポリシー（SELL 対象は BUY から除外）・ランク付けの再付与を実装。
  - Security
    - news_collector で defusedxml を採用し XML Bomb 等に対する対策を実施。
    - news_collector は受信バイト数上限や HTTP スキームチェック等を想定して SSRF/DoS の緩和を考慮。
    - jquants_client は認証トークン管理と自動リフレッシュを実装。ネットワークや HTTP エラーに対する再試行ロジックで堅牢性を向上。
  - Documentation / Notes
    - 各モジュールに docstring を充実させ、処理フロー・設計方針・期待されるテーブル名（例: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar）やカラムを明記。
    - リサーチコードは外部依存（pandas 等）を避け、標準ライブラリ + duckdb で動作する設計。
  - Known issues / TODO
    - signal_generator の _generate_sell_signals 内に記載の通り、以下のエグジット条件は未実装（将来実装予定）:
      - トレーリングストップ（peak_price に依存）
      - 時間決済（保有日数 60 営業日超）
      これらは positions テーブルに追加メタ情報（peak_price / entry_date 等）が必要。
    - news_collector の完全な実装（RSS パース → NewsArticle 抽出 → DB 保存の一連処理）は本リリースでは骨格とユーティリティを実装。RSS ソース追加やマッピングロジックは利用者が設定する必要あり。
    - duckdb 側のスキーマ（テーブルとカラム）は実装ポリシー文書に従って用意する必要あり（本リポジトリにスキーマ作成 SQL は含まれていない）。
  - Breaking Changes
    - 初回リリースのため該当なし。

補足（導入者向けメモ）
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 期待する DuckDB テーブル（代表例）
  - raw_prices, raw_financials, prices_daily, market_calendar, features, ai_scores, positions, signals, raw_news
- 主要依存（実行環境に必要なもの）
  - duckdb, defusedxml（news_collector の利用時）
- ログ出力は各モジュールに logger を利用しているため、アプリケーション側で logging.basicConfig 等を設定すると挙動観察が容易。

今後の予定（一例）
- positions テーブルを拡張してトレーリングストップ等のエグジットロジックを完全実装。
- news_collector のフルパイプライン実装とニュース→銘柄マッチング強化。
- テストカバレッジの拡充（ユニットテスト・統合テスト）。

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴やリリース管理方針に応じて調整してください。）