Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従って記録します。  
このファイルは Keep a Changelog の形式に準拠します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
  - モジュール公開: data, strategy, execution, monitoring を __all__ で公開

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定読み込みを自動化
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）
  - .env / .env.local の優先順位制御（OS 環境変数保護、override 機能）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスによる環境変数ラッパー（必須キーチェック、デフォルト値、バリデーション）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目の取得
    - DUCKDB_PATH / SQLITE_PATH のデフォルト値と Path 型変換
    - KABUSYS_ENV / LOG_LEVEL の許容値チェックと is_live/is_paper/is_dev ユーティリティ

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）でセンチメント評価
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当の UTC 計算）: calc_news_window
  - バッチ処理（最大 20 銘柄／API コール）・1 銘柄あたり記事数／文字数のトリム
  - OpenAI 呼び出しの冗長性対応: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
  - JSON Mode を前提にしたレスポンス検証と堅牢なパース（前後テキストの復元処理含む）
  - スコアクリッピング（±1.0）、部分成功時の DB 置換戦略（DELETE → INSERT、対象コード限定）
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す
  - テスト容易性: _call_openai_api の差し替えを想定

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定
  - マクロニュース抽出（マクロキーワードリスト）と OpenAI 呼び出し（gpt-4o-mini、JSON Mode）
  - リトライ・フェイルセーフ: API 失敗時は macro_sentiment=0.0 として継続
  - ルックアヘッドバイアス防止設計（内部で date.today()/datetime.today() を参照しない、prices_daily の date < target_date 条件）
  - 冪等的 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）で market_regime テーブルを更新
  - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す

- データ関連ユーティリティ（src/kabusys/data/*）
  - ETL 結果クラス ETLResult を公開（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py で ETLResult を再エクスポート）
    - ETL の取得数・保存数、品質チェック結果、エラー一覧を保持。has_errors / has_quality_errors / to_dict を提供
  - ETL パイプライン基盤（pipeline.py）
    - 差分取得・バックフィル・品質チェック方針の実装（J-Quants クライアントとの連携を想定）
    - テーブル存在確認・最大日付取得ユーティリティ等を提供
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録がない場合は曜日ベースのフォールバック（週末除外）
    - calendar_update_job による J-Quants からの差分取得と冪等保存（lookahead / backfill / sanity チェック）
    - 最大探索範囲を設定して無限ループを防止

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev（200 日 MA 乖離）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR / 20 日移動など）
    - calc_value: per, roe（raw_financials から直近財務データを取得）
    - DuckDB を用いた SQL ベースの実装で外部 API にアクセスしない設計
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 将来リターン（任意ホライズン）を LEAD で取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（有効レコードが 3 件未満の場合は None）
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（round で安定化）
    - factor_summary: count/mean/std/min/max/median の統計要約

- OpenAI クライアント使用時の設計配慮
  - gpt-4o-mini（JSON mode）を前提にしたプロンプト設計・出力検証
  - API 呼び出し失敗時の再試行（指数バックオフ）と非致命的フォールバック（例: macro_sentiment=0.0）
  - テスト向けに _call_openai_api を差し替え可能（unittest.mock.patch を想定）

- ロギングとエラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを実装（情報・警告・例外ログ）
  - DB 書き込みでのトランザクション（BEGIN/COMMIT/ROLLBACK）と ROLLBACK 失敗時の警告

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 環境変数保護: OS 環境変数を保護する protected キーセットを .env ロード時に確保
- 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、意図しない環境上書きを回避可能

Notes / 今後の注意点
- OpenAI API キーは api_key 引数で注入可能（テスト時に環境変数に依存しない実行が可能）
- DuckDB の executemany に空リストを渡せない制約に配慮した実装（空チェックあり）
- 日付操作は全て date/datetime オブジェクトで行い、ルックアヘッドバイアス対策として現在時刻参照を避ける設計
- jquants_client（kabusys.data.jquants_client）との連携を前提とするが、実際の API 呼び出しや保存処理は該当モジュールに依存

問い合わせ / 貢献
- バグ報告・機能要望は issue を作成してください。README / ドキュメントに沿って環境変数・DuckDB の準備を行った上で再現手順を添えてください。