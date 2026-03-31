CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
このリポジトリの初回公開リリースとしての変更点をまとめています。

Unreleased
----------

（現在のところ未公開の変更はありません）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - top-level の公開モジュール: data, strategy, execution, monitoring（__all__）。

- 環境設定管理モジュールを導入（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - 読み込み順序: OS 環境変数 ＞ .env.local ＞ .env。OS 環境変数は保護され上書きされない。
  - 自動ロードを無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォート外の # は直前がスペース/タブのときコメントとして扱う）。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などの必須プロパティ。
    - DUCKDB_PATH / SQLITE_PATH の既定値と Path 変換。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のヘルパー。

- AI 関連: ニュース NLP と市場レジーム検出（src/kabusys/ai/）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini / JSON Mode）でセンチメントを推定。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチ処理: 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたり最大 10 記事 / 最大 3000 文字にトリム。
    - API 呼び出し時の堅牢化: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score の存在と型検査、既知コードのみ採用）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はニュースタイトルに対するキーワードマッチ（複数キーワード列挙）。
    - LLM 呼び出しは gpt-4o-mini、JSON 出力を想定。API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - スコア合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - public API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。
    - テスト容易性のため内部の OpenAI 呼び出しをパッチ可能に設計。

  - AI パッケージ公開（src/kabusys/ai/__init__.py）で score_news をエクスポート。

  - 設計方針（両モジュール共通）:
    - datetime.today() / date.today() を参照せず、ターゲット日引数ベースで処理（ルックアヘッドバイアス回避）。
    - API 呼び出し失敗時はスキップ／フォールバックして例外を上位へ投げない（運用の安定性重視）。

- リサーチ用ユーティリティ（src/kabusys/research/）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム (1M/3M/6M)、200 日 MA 乖離、20 日 ATR（ボラティリティ）、20 日平均売買代金/出来高変化率などを DuckDB クエリで計算。
    - 関数: calc_momentum(conn, target_date), calc_volatility(conn, target_date), calc_value(conn, target_date)
    - raw_financials テーブルから PER/ROE を取得して計算。
    - データ不足時に None を返す設計。

  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman の ρ、有効レコードが 3 未満なら None）。
    - ランク変換ユーティリティ: rank(values)（平均ランク、同順位は平均を採用）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
    - research パッケージの公開（src/kabusys/research/__init__.py）で代表関数を再エクスポート。

- データプラットフォーム関連（src/kabusys/data/）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の値を優先し、未登録日は曜日ベース（平日）でフォールバックする一貫した振る舞い。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants API（jquants_client）から差分取得 → market_calendar へ冪等保存。バックフィルや健全性チェックを実装。
    - 内部ユーティリティ: _table_exists, _has_calendar_data, _fetch_is_trading など。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧等を保持）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映したユーティリティを実装（内部関数例: _table_exists, _get_max_date）。
    - data.etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。

  - jquants_client との連携点を想定（jquants_client.fetch_market_calendar / save_market_calendar を利用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API の利用:
  - score_news / score_regime は OPENAI_API_KEY（環境変数）または api_key 引数を必要とします。未設定時は ValueError を送出します。
  - LLM レスポンスの不確実性に対してはバリデーション・リトライ・フォールバック（0.0）で耐性を持たせていますが、実運用では API 使用料やレート制限を考慮してください。
- DuckDB に依存する挙動:
  - executemany に空リストを渡すと問題となるバージョン（例: DuckDB 0.10）があるため、空チェックを行ってから executemany を呼び出す実装になっています。
- 環境変数読み込み:
  - プロジェクトルート探索は __file__ を起点とするため、パッケージ配布後でも動作することを想定していますが、特殊なパッケージ配置時は自動読み込みが期待通り動作しない可能性があります。自動読み込みを無効にするフラグを用意しています。
- 一部想定される外部モジュール:
  - jquants_client（J-Quants API ラッパー）や openai SDK、duckdb が必要です。CI / 実行環境での依存関係管理に注意してください。

Migration
- なし（初回リリース）。

今後の予定（一例）
- strategy / execution / monitoring の実装拡張（発注ロジック・リアルタイム監視）。
- AI モデルやプロンプト改良、モデル切替オプションの追加。
- より細かい品質チェック・アラート機能の強化。

-----

この CHANGELOG はコード内の仕様・設計コメント、関数シグネチャ、ログ出力メッセージ、および定数定義から推測して作成しています。必要に応じて日付・文言の調整や項目の追加を行ってください。