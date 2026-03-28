CHANGELOG
=========

すべての重要な変更を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更項目はモジュール単位で要点を列挙しています（実装上の設計方針や注意点も含む）。
- 日付はリリース日を表します（推測に基づき記載）。

[Unreleased]
-------------

（現在なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを設定 (src/kabusys/__init__.py)。

- 環境設定・自動読み込み
  - 環境変数読み込みモジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルートを .git または pyproject.toml から検索して .env /.env.local を自動ロード（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env パーサを強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを正しく処理。
    - override / protected オプションにより OS 環境変数を上書きしない運用をサポート。
    - 必須環境変数取得用の _require と、Settings クラスを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須とするプロパティを用意。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH はデフォルト値を提供。
      - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の値検証を実装。
      - is_live / is_paper / is_dev のブールプロパティを提供。

- AI（ニュース NLP & レジーム判定）
  - ニュースセンチメントスコアリングモジュールを追加 (src/kabusys/ai/news_nlp.py)。
    - raw_news と news_symbols を集計して銘柄ごとのテキストを作成。
    - gpt-4o-mini を用いた JSON Mode で OpenAI に送信し、銘柄毎に -1.0〜1.0 のスコアを得る。
    - 1チャンクあたり最大 20 銘柄（_BATCH_SIZE）でバッチ化・並列処理相当のチャンク処理。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx サーバーエラーに対して指数バックオフでリトライ。
    - レスポンスの厳密なバリデーションと不正レスポンス時のフォールバック（スキップ）を実装。
    - スコアは ±1.0 にクリップ。書き込みは冪等に（対象 code の DELETE → INSERT）。
    - ルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を内部参照しない）。
    - テスト容易性のため _call_openai_api を差し替え可能。

  - 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う。
    - 設計上の特徴:
      - ma200_ratio は target_date 未満のデータのみを使用してルックアヘッドを防止。
      - マクロニュースは news_nlp のウィンドウ計算を利用して抽出、LLM 呼び出しは独自実装によりモジュール結合を低減。
      - OpenAI 呼び出しのリトライ/フォールバックロジックを搭載。API 失敗時は macro_sentiment = 0.0 として続行。
      - market_regime テーブルへの書き込みはトランザクションで冪等に行う（BEGIN/DELETE/INSERT/COMMIT）。
      - gpt-4o-mini を利用し、JSON レスポンスを期待。

- Data（ETL, カレンダー管理）
  - ETL パイプライン基盤を追加 (src/kabusys/data/pipeline.py)。
    - ETLResult データクラスを公開（re-export は src/kabusys/data/etl.py）。
    - 差分更新・backfill・品質チェックの設計を反映するユーティリティを実装。
    - jquants_client 経由の差分取得・保存と、品質チェックモジュールとの連携を想定した設計。
    - DuckDB を前提にしたテーブル存在チェックや最大日付取得ユーティリティを提供。

  - マーケットカレンダー管理モジュールを追加 (src/kabusys/data/calendar_management.py)。
    - market_calendar テーブルを参照して営業日判定・次/前営業日取得・範囲内営業日リスト取得・SQ日判定を提供。
    - DB 登録がない場合は曜日ベース（平日＝営業日）でフォールバックする一貫したロジックを実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に保存するジョブを実装。バックフィルや健全性チェックを導入。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) を設定して無限ループを防止。

- Research（ファクター計算・特徴量探索）
  - ファクター計算モジュールを追加 (src/kabusys/research/factor_research.py)。
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - Value: latest 財務データ（raw_financials）から PER / ROE を計算する calc_value を実装。
    - DuckDB SQL を多用し、外部 API に依存しない設計。

  - 特徴量探索モジュールを追加 (src/kabusys/research/feature_exploration.py)。
    - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21））、IC（Spearman）計算 calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas など外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。
    - rank は同順位に対して平均ランク処理を行う（丸めで ties を安定化）。

- パッケージ公開 / 再エクスポート
  - ai、research、data モジュールの __init__ で主要関数を再エクスポートし、外部からのアクセスを容易にした。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の必須化:
  - パッケージ稼働に必要な敏感情報は環境変数で必須化（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。コード内で明示的に _require により未設定時はエラーとなる。
- .env ファイル読み込みはデフォルトで有効だが、テストや CI のために KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / Implementation details / 動作に関する注意
- OpenAI クライアント:
  - gpt-4o-mini を想定し、Chat Completions API の JSON Mode を利用する設計。
  - OpenAI API キーは api_key 引数経由または環境変数 OPENAI_API_KEY から解決される（未設定時は ValueError を送出）。
  - テスト時には _call_openai_api を patch して差し替え可能。

- DuckDB 前提:
  - 多くの処理は DuckDB 接続 (duckdb.DuckDBPyConnection) を受け取り、prices_daily / raw_news / raw_financials / market_calendar / ai_scores / news_symbols 等のテーブルを参照・更新する。
  - 一部の SQL バインドや executemany の使い方は DuckDB のバージョン互換性（空リストバインド等）を考慮している。

- ルックアヘッドバイアス対策:
  - AI スコアリングおよびレジーム判定モジュールでは、内部で datetime.today()/date.today() を直接参照せず、外部から与えられる target_date を基準に過去データのみを使用するように設計されています。

- フェイルセーフ設計:
  - AI 呼び出しや API エラー時は例外を即座に上位へ投げず（特にスコア取得系）、フォールバック値（0.0 やスキップ）で継続する方針を取っています。ただし、DB 書き込み失敗など致命的な操作は例外として上位に伝播されます。

- テスト容易性:
  - OpenAI呼び出しやスリープ関数など差替え可能にし、ユニットテストでのモックを想定した実装になっています。

Breaking Changes
- 初回リリースのため該当なし。

Removed
- （初回リリースのため該当なし）

----
今後のリリース案（想定）
- モデル・プロンプト改善（より高精度な JSON パース堅牢化）
- 並列化・スループット改善（ニューススコアリングの同時実行）
- J-Quants クライアントのエラーハンドリング強化とリトライ制御の外部化
- テレメトリ／モニタリング（Slack 通知連携など）の追加

もし特定ファイルや変更点をより詳細に反映したい場合は、どのモジュールについて深掘りするかを教えてください。