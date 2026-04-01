CHANGELOG
=========

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- なし（初期公開バージョンは下記 0.1.0 を参照）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初回リリース (kabusys v0.1.0)
  - 全体:
    - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
    - パッケージ公開 API の基本モジュール群を整備（data, ai, research 等へ分割）。
  - 環境設定:
    - 環境変数/設定管理モジュールを実装（src/kabusys/config.py）。
      - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
      - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等の柔軟なパース処理を実装。
      - .env.local は .env を上書き（override）する仕様、ただし OS の環境変数は protected され上書きを抑止。
      - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
      - 必須変数取得ヘルパー _require() と Settings クラス（J-Quants, kabu API, Slack, DB パス, 監視閾値, 環境判定等）を提供。KABUSYS_ENV / LOG_LEVEL のバリデーションを実施。
  - データプラットフォーム:
    - ETL パイプライン用の基盤クラス ETLResult（src/kabusys/data/pipeline.py）を追加。ETL 実行結果・品質問題・エラー列挙用。
    - ETL 用ユーティリティを公開（src/kabusys/data/etl.py）。
    - マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
      - 営業日判定 (is_trading_day)、前後営業日取得 (next_trading_day / prev_trading_day)、期間内営業日取得 (get_trading_days)、SQ判定 (is_sq_day) を実装。
      - market_calendar テーブルがない場合は曜日ベースでフォールバック（週末を非営業日扱い）。
      - calendar_update_job: J-Quants から差分取得 → 冪等保存（ON CONFLICT 相当）・バックフィル・健全性チェックを実装。
    - jquants_client 連携を想定した設計（calendar/pipeline で参照）。（jquants_client は別モジュール想定）
  - AI（ニュース NLP / レジーム判定）:
    - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）。
      - target_date を基準としたニュースウィンドウ計算（calc_news_window）。
      - raw_news と news_symbols を結合して銘柄別に記事を集約し、銘柄ごとに最大記事数 / 文字数でトリム。
      - 最大 _BATCH_SIZE（20） 銘柄単位で OpenAI（gpt-4o-mini）へバッチ送信、JSON Mode 応答をパースして ai_scores テーブルへ置換（DELETE → INSERT）する処理を実装。
      - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とレスポンスの厳密なバリデーションを導入。レスポンス異常時は該当チャンクをスキップして継続（フェイルセーフ）。
    - 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
      - prices_daily / raw_news / market_regime テーブル参照、ma200 比率計算とマクロニュース抽出、OpenAI 呼び出し（独立実装）による macro_sentiment 評価、スコア合成、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
      - API失敗やパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
  - リサーチ / ファクター:
    - ファクター計算群を実装（src/kabusys/research/factor_research.py）。
      - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR・相対 ATR）、Liquidity（20日平均売買代金・出来高比率）、Value（PER / ROE）を prices_daily / raw_financials から計算。
      - 各関数は target_date を引数とし、(date, code) をキーとする dict のリストを返す設計。
    - 特徴量解析ユーティリティ（src/kabusys/research/feature_exploration.py）。
      - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（calc_ic）計算（スピアマンのランク相関）、rank、factor_summary（基礎統計量）を標準ライブラリのみで実装。
    - 研究向け API を __all__ で再公開（zscore_normalize など）。
  - データ処理の堅牢性設計:
    - すべての「日付基準処理」は datetime.today()/date.today() に依存しない（ルックアヘッドバイアス防止）。target_date ベースでウィンドウやクエリを決定。
    - DuckDB を主要 DB として使用。複数箇所で executemany の空リスト回避など互換性考慮を実装。
    - DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT 相当）して部分失敗時の既存データ保護を行う。

Changed
- （初回リリース）コード構成・命名規約を明確化し、モジュール分割により責務を分離。

Fixed
- N/A（初回リリース）

Security
- 環境変数の取り扱いを慎重に実装:
  - OS 環境変数を protected として .env 読み込みでの上書きを抑止。
  - 必須 API キー (OPENAI_API_KEY 等) は明示的に要求し未設定時は ValueError を発生させる（呼び出し側での明示的な対応を促す）。

Notes / Limitations
- OpenAI への実際の呼び出しは外部ネットワークを伴うため、テスト時は内部の _call_openai_api を差し替えてモック化することを想定。
- 一部モジュールは jquants_client 等の外部クライアントの存在を前提としている（別途実装が必要）。
- ETL / calendar のジョブは外部 API の可用性とデータの前提に依存するため、運用時に適切な監視/再試行戦略を検討してください。

Authors
- kabusys 開発チーム（コードベースから推測して記載）

License
- ソースコード中にライセンス明示が無いため、利用・配布に際してはリポジトリの LICENSE を確認してください。