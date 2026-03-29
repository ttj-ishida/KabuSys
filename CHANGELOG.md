Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
リリース日はコードベースから推測して付記しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ初期構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定 / ロード機構（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点とするため CWD に依存しない。
  - .env のパース機能を実装（コメント、export 形式、シングル/ダブルクォートおよびバックスラッシュエスケープ対応）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリケーションで使用する主要な設定値をプロパティ経由で取得可能：
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルト値: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL
    - env 判定ヘルパー: is_live / is_paper / is_dev
  - 設定が不正な場合は適切に ValueError を送出するバリデーションを追加。

- データ関連（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを追加。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティを実装。
    - backfill / calendar lookahead 等のデフォルトポリシーを定義。
    - ETL のエラー／品質問題を収集して上位に伝える設計（Fail-Fast しない）。
  - ETL の公開インターフェースを kabusys.data.etl で再エクスポート（ETLResult）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にデータがない場合は曜日ベース（土日）でフォールバック。
    - calendar_update_job を実装し、J-Quants クライアントからの差分取得と冪等更新（ON CONFLICT 想定）を実施。バックフィル、健全性チェックを含む。
  - jquants_client の利用を前提とした設計（fetch/save の抽象化を想定）。

- 研究（research）パッケージ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム：mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離率）
    - ボラティリティ／流動性：atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio
    - バリュー：per（株価 / EPS, EPS が 0/欠損なら None）、roe（財務データから取得）
    - DuckDB を用いた窓関数ベースの計算実装。データ不足時は None を返すロバスト設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（結合と欠損除外、3件未満は None）
    - ランキングユーティリティ（rank）: 同順位は平均ランク、丸めによる ties 対応
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出（None を除外）
  - データ統計ユーティリティ zscore_normalize は kabusys.data.stats から再エクスポート（__init__ で公開）。

- AI / ニュース NLP（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を使い、銘柄別に記事を集約して OpenAI（gpt-4o-mini）にバッチ送信しスコアを取得。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用（calc_news_window を提供）。
    - チャンク処理（最大 20 銘柄／チャンク）、1 銘柄あたり最大記事数と文字数でトリムする保護（トークン肥大対策）。
    - JSON Mode を想定したレスポンス検証（results 配列、code/score の形式検証、スコアは ±1.0 にクリップ）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。中断はログ出力して継続（フェイルセーフ）。
    - DB 書き込みは部分的失敗に強い設計（取得済みコードのみ DELETE → INSERT）で既存スコア保護。
    - テスト用フック: _call_openai_api のモック差し替えを想定。
  - マクロレジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、ニュース NLP のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily の日次データと raw_news を用いる。LLM 呼び出しは gpt-4o-mini を使用。
    - ルックアヘッドバイアス対策: target_date 未満のデータのみ参照、datetime.today() 参照禁止設計。
    - API エラー時は macro_sentiment を 0.0 にフォールバック、冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実行。
    - リトライとエラー分類を実装（RateLimit / Connection / Timeout / APIError の取り扱い）。
    - テスト用フック: _call_openai_api のモック差し替えを想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは api_key 引数でも指定可能だが、環境変数 OPENAI_API_KEY からの読み取りをサポート。必須未設定時は ValueError を送出して失敗モードを明確化。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策が設計指針として一貫して適用されている（datetime.today()/date.today() を AI スコア関数で参照しない、prices_daily クエリは target_date 未満の排他条件など）。
- DuckDB を分析基盤として前提（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）。
- API 呼び出しは冪等性と堅牢性を重視（リトライ、フォールバック、部分書き込みで既存データ保護）。
- テスト容易性のため、OpenAI 呼び出し部分はモック差替えができるように実装されている。
- .env パーサーは一般的なケース（コメント、export、クォート、エスケープ）に対応しているが、極端に複雑な .env 構文は未検証。

---

開発を継続する際は、次のバージョンで以下を追記することを推奨します:
- API クライアント（jquants_client / kabu_stn_client 等）の具体的実装とバージョン互換性の明記
- 追加された CLI / サービス起動スクリプト、監視（monitoring）や実行（execution）周りの詳細
- テストカバレッジ・型チェック・CI ワークフローの導入履歴