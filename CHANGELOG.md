CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- 今後のリリースでの変更点をここに記載します。

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース: kabusys パッケージの公開。
  - パッケージ構成: kabusys.{data,research,ai,execution,monitoring,config} を想定したモジュール群を提供。
  - バージョン: __version__ = "0.1.0"

- 環境・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理の扱いの明確化。
    - キーの上書き制御（override と protected set）により OS 環境変数の保護を実現。
  - Settings クラスを提供し、以下の設定プロパティを安全に取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH (Path 型で展開)
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols テーブルを読み、OpenAI (gpt-4o-mini, JSON mode) を使って銘柄ごとのセンチメント ai_score を算出する score_news(conn, target_date, api_key=None) を実装。
  - 処理の特徴:
    - JST ベースのニュース取得ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換して比較）。
    - 1銘柄あたり最新記事を最大 _MAX_ARTICLES_PER_STOCK 件、かつ最大文字数でトリムしてプロンプトに含める。
    - 最大 _BATCH_SIZE（デフォルト 20）銘柄ずつバッチで API 呼び出し。
    - 429/ネットワーク切断/タイムアウト/5xx を対象に指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション: JSON 抽出（前後ノイズの復元含む）、"results" 配列構造検査、コード正規化、スコア数値検査、スコアを ±1.0 にクリップ。
    - 書き込みは冪等: 取得済み銘柄のみ DELETE → INSERT（部分失敗時に他銘柄の既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api のパッチ等を想定）。
  - エラー時の挙動: API キー未指定で ValueError。API 失敗時は該当チャンクをスキップし処理継続。

- レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime(conn, target_date, api_key=None) を実装。
  - 処理の特徴:
    - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドを排除。
    - マクロニュースは news_nlp.calc_news_window に基づいて抽出し、OpenAI による JSON レスポンス（{"macro_sentiment": float}）をパース。
    - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。429/タイムアウト等は再試行（リトライ上限あり）。
    - レジームスコアはクリップされ、閾値によりラベルを付与。
    - 書き込みは冪等なトランザクション（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。

- データ ETL / パイプライン (src/kabusys/data/pipeline.py, etl.py)
  - ETLResult データクラスを公開（etl.ETLResult を再エクスポート）。
  - ETL パイプライン設計（差分更新、backfill、品質チェック、idempotent 保存）に基づいたユーティリティ実装の骨子を含む。
  - DuckDB を前提に最大日付取得やテーブル存在チェック等のヘルパーを提供。

- マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダーの夜間バッチ更新ロジック calendar_update_job(conn, lookahead_days=...) を実装。
    - J-Quants からの差分取得、バックフィル (直近 _BACKFILL_DAYS 日)、健全性チェック（未来日付の異常検出）を実装。
    - 取得 → jquants_client.save_market_calendar による冪等保存を想定。
  - 営業日判定ユーティリティを提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar テーブルの有無や未登録日の取り扱いでは曜日ベースのフォールバック（週末除外）を一貫して使用。
    - 探索上限 (_MAX_SEARCH_DAYS) を設け、無限ループ防止。
  - DB 値優先、未登録日は曜日フォールバックという挙動を一貫して適用。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials からの EPS/ROE を用いて PER/ROE を計算（EPS 欠損/0 の場合は None）。
    - DuckDB SQL を活用した実装で、外部 API にアクセスしない設計。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（営業日ベース）を一括取得する汎用関数。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装（有効レコード < 3 の場合は None）。
    - rank(values): 同順位は平均ランクにするランク化関数（数値丸めにより ties 検出の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す統計サマリ。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いに配慮:
  - OS 環境変数は protected として .env による上書きを防止。
  - OpenAI API キー等の必須機密情報は明示的に要求し、未設定時は ValueError を発生させることで誤使用を防止。

Notes / Known limitations
- OpenAI（gpt-4o-mini）を使用する箇所は API キーが必須。未設定時は ValueError を投げる。
- LLM レスポンスの不確実性・API 失敗に備え、失敗時は 0.0 を用いるなど保守的なフォールバックを採用しているため、時にはスコアが欠落（チャンクスキップ）することがある。
- 一部の DuckDB executemany 呼び出しについては空リスト渡しを避ける実装上の注意（DuckDB 0.10 互換性）。
- 一部関数はデータ不足時に None を返す仕様（ファクター・ATR・MA200 等）。呼び出し側での取り扱いが必要。

後続作業候補（今後のリリースで検討）
- execution / monitoring モジュールの実装拡張（実際の発注ロジックや監視通知の充実）。
- ai モジュールのテスト用モックやローカルフェイルオーバーの強化。
- 品質チェックモジュール（kabusys.data.quality）の詳細な実装と ETL ワークフローとの統合。
- ドキュメント（API リファレンス、設計ドキュメント）の整備。

-----------------------------------------------------------------------------