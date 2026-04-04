CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリースは日付順（新しい順）で記載します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- 初回公開リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理:
  - src/kabusys/config.py を追加。
    - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env パース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを提供（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境・ログレベル判定等）。
    - 必須環境変数未設定時に ValueError を送出するヘルパー _require。
    - 環境変数のデフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, PID_FILE_PATH 等）。

- ニュース NLP（AI）:
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini + JSON Mode）でセンチメントスコアを算出。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数上限）、JSON レスポンス検証、スコアの ±1.0 クリップ。
    - リトライ/バックオフ: 429（RateLimit）、ネットワーク断、タイムアウト、5xx を指数バックオフで再試行。
    - フェイルセーフ設計: API 失敗やパース失敗時は該当チャンクをスキップして処理継続。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を通す（unittest.mock.patch で差し替え可能）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 結果を書き込んだ銘柄数を返す。

  - src/kabusys/ai/__init__.py で score_news を公開。

- 市場レジーム判定（AI + 価格指標の融合）:
  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム ('bull' / 'neutral' / 'bear') を判定・保存。
    - prices_daily / raw_news / market_regime テーブルを利用。
    - OpenAI 呼び出しに対する堅牢なリトライ処理、API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - レジーム算出はルックアヘッドバイアス回避（target_date 未満のみ参照）に配慮。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- リサーチ（ファクター計算・特徴量探索）:
  - src/kabusys/research/ 以下を追加。
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム系ファクターを計算。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比などのボラティリティ / 流動性指標を計算。
      - calc_value: raw_financials から直近財務を取得し PER / ROE を算出。
      - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
    - feature_exploration.py:
      - calc_forward_returns: 指定ホライズン先の将来リターンを一括で取得（デフォルト [1,5,21]）。
      - calc_ic: スピアマン（ランク）による IC 計算（ファクターと将来リターンの関連）。
      - rank: 同順位は平均ランクで処理するランク化ユーティリティ。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - research パッケージ __all__ で主要関数を公開。
    - zscore_normalize は kabusys.data.stats から利用可能。

- データプラットフォーム:
  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar に基づく営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値がない場合の曜日ベースフォールバック、最大探索日数の安全制約、JPX カレンダー差分取り込みジョブ（calendar_update_job）。
    - J-Quants クライアントとの連携箇所を想定（jquants_client）。
  - src/kabusys/data/pipeline.py を追加。
    - ETLResult データクラス（ETL 実行結果のまとめ、品質問題やエラー一覧を保持）。
    - 差分取得・保存・品質チェックの流れを想定したユーティリティ（バックフィル日数等のデフォルト設定）。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- 実装方針・運用上の注意点（ドキュメント的追加）
  - 多くのモジュールで「ルックアヘッドバイアス防止」を明示（datetime.today()/date.today() を直接参照しない）。
  - OpenAI API 呼び出しは明示的な api_key 引数を受け付け、引数未指定時は環境変数 OPENAI_API_KEY を参照。
  - API 失敗時のフェイルセーフ動作（neutral/0.0扱い、部分スコア処理保持）を採用し、処理全体の継続性を重視。
  - テストフレンドリーな設計（内部の API 呼び出しポイントをモック差し替え可能にしている）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）、KABU_API_PASSWORD（kabuステーション API 用）は Settings で必須となる（未設定時は ValueError）。
  - OpenAI を利用する機能（score_news, score_regime）は OPENAI_API_KEY が必要。各関数は api_key 引数で明示的に渡せる。
- デフォルト DB パス等:
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
- 自動 .env 読み込み:
  - プロジェクトルートが検出できない場合、自動読み込みはスキップされる。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

今後の予定（短評）
- strategy / execution / monitoring パッケージの実装とそれらの統合テストを予定。
- データ品質チェック（quality モジュール）や jquants_client の詳細実装／テストカバレッジの強化。
- 実運用に向けた監視・ロギング・エラーアラートの整備。

---
以上。