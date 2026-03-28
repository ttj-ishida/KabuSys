# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28

初回リリース — 日本株自動売買サポートライブラリ「KabuSys」v0.1.0

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。公開 API として data, strategy, execution, monitoring を __all__ で明示。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパース機能を実装（コメント、export プレフィックス、クォート／エスケープ対応）。無効行は無視。
  - Settings クラスを提供し、アプリケーションで利用する主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）および補助プロパティ is_live/is_paper/is_dev
  - 必須環境変数未設定時は ValueError を送出する _require を実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウ定義（JST 前日 15:00 〜 当日 08:30 → UTC で前日 06:00 〜 23:30）を計算する calc_news_window を提供。
    - API 呼び出しはチャンク（デフォルト 20 銘柄）単位で行う。1 銘柄あたりの記事数・文字数上限を設けてトークン肥大化を抑制。
    - レスポンスの厳密バリデーション・JSON 復元ロジックを実装。スコアは ±1.0 にクリップして ai_scores テーブルへ書き込む（部分置換: 対象コードのみ DELETE → INSERT）。
    - ネットワーク断・429・タイムアウト・5xx は指数バックオフでリトライ。失敗時は該当チャンクをスキップして他の銘柄処理を継続（フェイルセーフ）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロセンチメントはニュースタイトル（マクロキーワードによる抽出）を LLM（gpt-4o-mini, JSON mode）で評価して取得。
    - API 再試行・フェイルセーフ・レスポンスパース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。公開関数: score_regime(conn, target_date, api_key=None) → 1 を返す。
- データモジュール (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得→保存）。
    - 営業日判定・翌営業日/前営業日/期間内営業日取得・SQ日判定の一貫したロジックを提供（DB 優先、未登録日は曜日ベースでフォールバック）。
    - 最大探索日数やバックフィル/健全性チェック等の安全措置を導入。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を格納する ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client の save_* を前提に idempotent 保存）、品質チェックのための結果収集をサポートするユーティリティを実装。
    - DuckDB との互換性を考慮したユーティリティ（テーブル存在確認、最大日付取得など）を提供。
- リサーチ機能 (kabusys.research)
  - factor_research モジュールで以下のファクター計算を実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新値を使用）
  - feature_exploration モジュールで以下を実装:
    - calc_forward_returns: 指定ホライズンに対する将来リターンの計算（horizons の妥当性検査あり）
    - calc_ic: スピアマンランク相関（IC）計算（有効レコード不足時は None）
    - rank: ランク化ユーティリティ（同順位は平均ランク）
    - factor_summary: 各ファクターの統計サマリー（count/mean/std/min/max/median）
  - zscore_normalize は kabusys.data.stats から再エクスポート（research/__init__ でまとめて公開）。
- テスト・拡張性を考慮した設計
  - OpenAI API 呼び出しは内部で _call_openai_api として分離しており、テスト時にモック可能（unittest.mock.patch を想定）。
  - 日時処理は内部で date / datetime を明示的に扱い、datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。

### 修正 (Changed)
- 初版リリースのため該当なし。

### 修正 (Fixed)
- 初版リリースのため該当なし。

### 既知の注意点 / 破壊的変更の可能性 (Notes / Breaking Changes)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須となっており、未設定時は ValueError が発生します。
  - OpenAI を使う score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY の設定が必須です。未設定時は ValueError を送出します。
- .env 自動ロード:
  - 自動ロードはデフォルトで有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB 互換性:
  - DuckDB に対する executemany で空リストを渡すとエラーになることを考慮し、空チェックを導入しています（DuckDB 0.10 の制約への対応）。
- OpenAI とのやり取り:
  - gpt-4o-mini と JSON mode（response_format={"type": "json_object"}）を利用。API レスポンスが期待の JSON 構造でない場合は安全にスキップし、処理は継続します。
  - レスポンスのパースや LLM 出力の不正に対してはフォールバック（0.0 など）を使用して例外を上位に波及させない方針です。重大な DB 書き込み失敗時は例外を伝播します。
- 日付の取り扱い:
  - ニュースウィンドウ等は JST を基準に UTC naive な datetime を生成して DB 比較に使用します。target_date の解釈に注意してください。
- ロギングと検証:
  - 各処理は詳細なログを出力します。設定の LOG_LEVEL と KABUSYS_ENV の値はバリデーションがあります。

---

以上が v0.1.0 の主要な追加点と注意事項です。今後のリリースではバグ修正、API の安定化、追加の戦略・実行モジュールの実装等を予定しています。もし changelog に追記したい事項や誤りがあればお知らせください。