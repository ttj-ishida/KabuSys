CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog に準拠。  
バージョン番号はパッケージ内の __version__ に合わせています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース。日本株自動売買システムのコアモジュール群を追加。
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - __all__ に ["data", "strategy", "execution", "monitoring"] を設定（公開サブパッケージの意図を明示）
  - 設定 / 環境変数管理 (kabusys.config)
    - .env ファイルおよび環境変数から設定を読み込む自動ローダを追加（プロジェクトルート検出: .git または pyproject.toml）。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサ実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のエスケープ処理対応
      - コメント処理（クォート外かつスペース前の # をコメントと判定）
    - Settings クラスを提供（settings インスタンスをエクスポート）。
      - 必須設定取得メソッド（未設定時は ValueError を送出）:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - オプション・既定値:
        - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
        - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
        - SQLITE_PATH（デフォルト: data/monitoring.db）
      - システム設定検証:
        - KABUSYS_ENV: 有効値 {"development","paper_trading","live"}。不正値は ValueError。
        - LOG_LEVEL: 有効値 {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}。不正値は ValueError。
      - ラッパープロパティ: is_live / is_paper / is_dev
  - AI（自然言語処理）モジュール (kabusys.ai)
    - news_nlp.score_news
      - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI (gpt-4o-mini) に送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存。
      - 日次ウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換してDB参照）。
      - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄当たり最大 10 記事、最大 3000 文字にトリム。
      - JSON Mode を前提とした厳密な JSON 出力期待（レスポンスの復元ロジックあり）。
      - リトライ/バックオフ: 429・ネットワーク切断・タイムアウト・5xx を対象に指数バックオフでリトライ（最大試行回数制御）。
      - フェイルセーフ: API 例外やパース失敗時は該当チャンクをスキップして継続。最終的に取得したスコアのみ書き換え（DELETE → INSERT）し、部分失敗時に既存データを保護。
      - テスト用フック: _call_openai_api をパッチして差し替え可能。
    - regime_detector.score_regime
      - ETF 1321（225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
      - マクロニュースは news_nlp.calc_news_window を用いて対象ウィンドウから抽出し、OpenAI で -1.0〜1.0 を評価（gpt-4o-mini を使用）。
      - レジームスコア合成とラベリング: clip 後にしきい値により "bull"/"neutral"/"bear" を判定。
      - フェイルセーフ: API エラー時は macro_sentiment を 0.0 にフォールバックし処理継続。
      - DB 書込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。書込み失敗時は ROLLBACK を試行し例外を上位へ伝播。
  - Research（ファクター・特徴量探索）モジュール (kabusys.research)
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）。
      - 出力形式はリストの dict（各要素に date, code を含む）。データ不足時は None を返す項目あり。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを計算。horizons の検証あり（1〜252）。
      - calc_ic: スピアマンランク相関（IC）を実装。3 レコード未満で計算不能 → None。
      - rank: 同順位は平均ランクで処理（浮動小数誤差対策に round(v,12) を利用）。
      - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
    - 研究 API は DuckDB の prices_daily / raw_financials テーブルのみ参照（本番アクションは行わない設計）。
  - Data（データ管理 / ETL）モジュール (kabusys.data)
    - calendar_management:
      - 市場カレンダー（market_calendar）を用いた営業日判定関数を提供:
        - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
      - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末は非営業日）。
      - next/prev_trading_day は探索上限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
      - calendar_update_job: J-Quants API からの差分取得 → jq.save_market_calendar による冪等保存。バックフィル・健全性チェックを実施。
    - pipeline / etl:
      - ETLResult データクラスを公開（ETL 実行の取得数/保存数、品質問題、エラーを格納）。
      - pipeline モジュール設計（差分更新、backfill、品質チェックの考慮）に基づくユーティリティを実装。
      - DuckDB のテーブル有無や最大日付を取得するユーティリティを含む。
    - 注意: これらは主に jquants_client（外部 API クライアント）との連携を前提としている（kabusys.data.jquants_client を呼び出す実装あり）。
  - テスト・運用を意識した設計点（全体）
    - ルックアヘッドバイアス防止のため、datetime.today() / date.today() をアルゴリズム内部で直接参照しない方針（引数で target_date を受け取る）。
    - OpenAI 呼び出しは各モジュールで独立実装し、モジュール間でプライベート関数を共有しない（テストでの差し替えを容易にするため）。
    - API 呼び出しでの失敗は局所的にフォールバック処理を行い、例外がシステム全体を停止させないように設計。
  - 依存と期待される DB スキーマ（概要）
    - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブルを想定。
    - DuckDB を主要なローカル分析 DB として使用。

Fixed
- 初版のため該当なし。

Changed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出して漏洩リスクを低減。
- .env 読み込み時に OS 環境変数の上書きを防ぐため protected set（既存 os.environ）を尊重する実装を導入。

Notes / 使用上の注意
- OpenAI 連携
  - 使用モデル: gpt-4o-mini（JSON Mode を利用）
  - レスポンスは厳密な JSON を期待するが、余計な前後テキストが混入するケースへの復元ロジックあり。
  - API エラーや JSON パース失敗は局所的にログ出力してフォールバック（例: macro_sentiment=0.0、チャンクスキップ）するため、呼び出し側は戻り値や影響範囲を確認してください。
- 環境変数
  - 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
  - settings の必須項目が未設定の場合、アプリケーション起動時またはそれらプロパティ参照時に ValueError が発生します。
- DB 書き込み
  - ai_scores / market_regime などのテーブル書き込みは冪等性を考慮して削除→挿入の流れをとっています。部分失敗時のデータ保護のため、書込対象コードを絞って実行します。

今後の予定（未実装・拡張候補）
- strategy / execution / monitoring の具体実装（パッケージ公開は __all__ に含めているが本リリースでは未実装の可能性あり）。
- 追加の品質チェックルールや監査ログの充実。
- モデルパラメータやしきい値の環境変数化・チューニング用インタフェース。

---