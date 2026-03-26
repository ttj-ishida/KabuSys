# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

---

[0.1.0] - 2026-03-26
======================================
初期リリース

Added
-----
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py にてバージョン (0.1.0) と公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 設定／環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を上位ディレクトリで探索）。
  - .env パーサを実装（コメント行、export プレフィックス、シングル／ダブルクォート、エスケープ処理、行内コメントの取り扱いに対応）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 必須設定取得用の _require 関数と Settings クラスを提供。以下の主要設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 環境変数未設定時は ValueError を発生させる安全な取得方法を提供。

- AI（Natural Language）モジュール (kabusys.ai)
  - ニュースセンチメント分析: score_news を実装（kabusys.ai.news_nlp）
    - 前日15:00 JST〜当日08:30 JST に相当する UTC 時間ウィンドウでニュースを集計（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄毎に最新記事を集約（最大記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini、JSON mode）へバッチ送信（チャンクサイズ 20 銘柄）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでの再試行。
    - レスポンスの厳密なバリデーション（JSON 再抽出処理、results 配列・code/score 検証、数値クリップ ±1.0）。
    - 書き込みは冪等性を考慮：対象 code のみ DELETE → INSERT（DuckDB の executemany の挙動に配慮）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

  - 市場レジーム判定: score_regime を実装（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200 の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタ。記事が存在する場合のみ LLM を呼び出し。
    - OpenAI 呼び出しは独立実装でテスト容易性を確保。API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時はロールバック。

  - AI モジュール共通
    - gpt-4o-mini を利用する想定。JSON Mode のレスポンス処理や retry/backoff のポリシーが組み込まれている。
    - テスト用に API 呼び出し関数をモジュールローカルにし、patch で差し替え可能に設計。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先し、未登録日は曜日（平日）ベースでフォールバックする一貫した挙動。
    - next/prev_trading_day は探索上限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
    - jquants_client 経由での取得・保存処理に対応。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得数、保存数、品質問題、エラー集約など）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの統合）を想定した設計。
    - DuckDB を前提とした最大日付取得ユーティリティ、テーブル存在確認などを含む。

- Research モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ／流動性: calc_volatility（20 日 ATR、ATR 比、平均売買代金、出来高比率）
    - バリュー: calc_value（PER、ROE。raw_financials から最新財務を取得）
    - 各関数は prices_daily / raw_financials のみを参照し、結果を [{date, code, ...}] 形式で返す。
    - データ不足時の None 戻りや適切なウィンドウ制御を実装。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（複数ホライズンに対応、引数検証）
    - IC 計算: calc_ic（スピアマンρ ランク相関、3 サンプル未満は None）
    - ランク変換: rank（同順位は平均ランク、丸め対策あり）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）
    - pandas 等の外部ライブラリに依存せず、標準ライブラリと DuckDB で実装。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- OpenAI / J-Quants / Kabus API 等の機密情報は環境変数管理を前提。必須トークン未設定時は明示的に ValueError を発生させる設計。

Notes / 設計上の重要点
-------------------
- ルックアヘッドバイアス回避:
  - AI スコア生成・レジーム判定・ファクター計算等はすべて target_date 引数を受け取り、内部で datetime.today()/date.today() を参照しない設計。
  - DB クエリは target_date より前（排他）や LEAD/LAG を使った運用などで将来データを参照しないよう注意。

- 冪等性と部分失敗耐性:
  - DB への書き込みは DELETE→INSERT 等で対象コードを限定することで、部分失敗時に既存データを不必要に消さない。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた保護。

- テスト容易性:
  - OpenAI 呼び出し部分はモジュールローカル関数で実装し、patch による差し替えを想定。

- DuckDB 互換性への配慮:
  - executemany に空リストを渡さない等、DuckDB のバージョン挙動に対する防御的コーディングを行っている。

今後（提案）
-----------
- 戦略（strategy）、発注（execution）、モニタリング（monitoring）パッケージの実装拡張（初期構成では __all__ に名前を露出）。
- カバレッジ向上のためユニットテスト（特に外部 API 呼び出しと DB 書き込みのモック）。
- 性能改善（大量銘柄・長期間の ETL に対する最適化）や observability（監査ログ、メトリクス）の追加。

---

（注）本 CHANGELOG は提供されたソースコードからの実装内容を推測して作成しています。実装外の機能や将来的な変更は反映されていません。