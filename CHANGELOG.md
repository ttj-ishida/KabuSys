CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従って記載しています。

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース。パッケージ名: kabusys (バージョン 0.1.0)
- 基盤 / 設定
  - 環境変数・設定管理モジュールを追加（kabusys.config）
    - .env / .env.local をプロジェクトルートから自動読み込み（優先順位: OS 環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能（テスト用途）。
    - 高度な .env 行パーサ実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
    - 環境変数必須チェック用の _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティを含む）。
    - 設定値の妥当性検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの基本型を追加（kabusys.data.pipeline）
    - ETLResult データクラスを公開（保存レコード数、品質チェック結果、エラー等を集約）。
    - 差分取得・バックフィル・品質チェックを想定した設計（id_token 注入可）。
  - カレンダー管理モジュールを追加（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - calendar_update_job（J-Quants から差分取得して冪等保存）
    - DB にデータがない/未登録日の場合は曜日ベースでフォールバックする堅牢な設計。
    - 最大探索日数・バックフィル・健全性チェック等のサニティ機構を実装。
  - etl / pipeline モジュールにおける DuckDB 互換性考慮（executemany に空リストを渡さない等）。

- リサーチ（特徴量・ファクター）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - Value（PER、ROE：raw_financials からの取得）
    - すべて DuckDB 上の prices_daily / raw_financials のみ参照する設計。外部 API にアクセスしない。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン算出（calc_forward_returns、ホライズン指定可能）
    - IC（Information Coefficient）計算（calc_ic）
    - 統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）
  - re-export:
    - kabusys.research.__init__ で zscore_normalize（kabusys.data.stats 由来）を含む主要関数を再エクスポート。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのスコアを ai_scores テーブルに書き込む。
    - 時間ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）、記事トリム（最大記事数 / 最大文字数）によるトークン肥大化対策。
    - JSON mode を利用した厳密なレスポンス期待、レスポンス検証および数値クリップ（±1.0）。
    - レート制限(429)/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライを実装。失敗時は個別チャンクをスキップして処理継続（フェイルセーフ）。
    - DuckDB との互換性（部分書き換えのため DELETE→INSERT 順の冪等処理）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（"bull"/"neutral"/"bear"）を判定。
    - calc_news_window を用いたニュースウィンドウ取得、_calc_ma200_ratio、_fetch_macro_news、OpenAI 呼び出し、冪等な market_regime への書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- その他
  - パッケージ初期化で主要サブパッケージを __all__ に登録（data, strategy, execution, monitoring）。
  - AI モジュールのテスト容易性を考慮し、内部の OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch を想定）。
  - ロギングによる詳細な情報・警告出力を多用し問題の追跡を容易化。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - 日付関連処理（score_news, score_regime, ファクター計算等）は内部で datetime.today() / date.today() を直接参照しない設計。すべて target_date ベースで計算します。
- フェイルセーフ:
  - 外部 API（OpenAI、J-Quants）呼び出しの失敗は個別処理単位でフォールバックまたはスキップされ、全体処理が致命的に停止しない設計としています（ただし DB 書き込み失敗時は例外を伝播）。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになるバージョン互換性を回避するため、事前に空判定してから実行します。
- 環境変数の保護:
  - .env ロード時、既存の OS 環境変数はデフォルトで保護され、.env.local は override=True で後から上書き可能（ただし OS 環境変数は protected）。

今後の予定（想定）
- strategy / execution / monitoring パッケージの実装拡充（現時点ではパッケージ参照のみ）。
- J-Quants クライアントの詳細実装や ETL のジョブ化、モニタリング用 DB スキーマ整備。
- テストカバレッジの追加（特に OpenAI 呼び出しや DB 部分のモックテスト）。

--- 

この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合はお知らせください。