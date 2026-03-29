# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

最新リリース
------------

### [0.1.0] - 2026-03-29

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0"
  - パブリックサブパッケージ: data, strategy, execution, monitoring（__all__）

- 設定 / 環境変数管理
  - .env ファイルおよび環境変数の自動読み込み機能を実装（src/kabusys/config.py）
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
    - .env パーサ: export プレフィックス対応、クォート内のバックスラッシュエスケープ、行末コメント処理等をサポート
    - 上書き制御と protected（OS 環境変数の保護）オプション
  - Settings クラスを提供（settings インスタンス）
    - J-Quants / kabuステーション / Slack 用の必須環境変数取得メソッド
    - DB パスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）
    - env / log_level の検証（許容値チェック）および is_live / is_paper / is_dev ヘルパー

- AI ニュース NLP
  - ニュース記事の銘柄ごとのセンチメントスコアリング機能を実装（src/kabusys/ai/news_nlp.py）
    - タイムウィンドウ算出（前日15:00 JST ～ 当日08:30 JST を UTC に変換）
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約
    - 1チャンク最大 20 銘柄で OpenAI（gpt-4o-mini）にバッチ送信（JSON Mode）
    - トークン肥大化対策（1銘柄あたり最大記事数 / 最大文字数でトリム）
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
    - レスポンスの堅牢なバリデーション（JSON 復元、results 配列、コード照合、数値チェック）
    - スコアは ±1.0 にクリップし、ai_scores テーブルに冪等的に書き込み（DELETE → INSERT）
    - API キー注入（引数優先、なければ OPENAI_API_KEY 環境変数）

- 市場レジーム判定（Regime Detector）
  - ETF 1321（Nikkei 225 連動型）200日移動平均乖離とマクロセンチメントを合成して日次レジームを判定（src/kabusys/ai/regime_detector.py）
    - ma200_ratio 計算（target_date 未満のデータのみを使用しルックアヘッドバイアスを防止）
    - マクロキーワードで raw_news をフィルタリングし、LLM（gpt-4o-mini, JSON Mode）で macro_sentiment を評価
    - 重み付け（MA 70%、マクロ30%）でスコア合成、閾値で bull/neutral/bear を判定
    - OpenAI 呼び出しのリトライ・バックオフ、API 失敗時は macro_sentiment=0.0 のフォールバック
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）

- データプラットフォーム（Data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ロジック
    - market_calendar が無い場合の曜日ベースフォールバック（週末は非営業日）
    - calendar_update_job: J-Quants からの差分取得と市場カレンダーの夜間更新（バックフィル・健全性チェック・冪等保存）
    - 最大探索日数の制限で無限ループを防止
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（取得数、保存数、品質問題、エラー一覧など）
    - 差分更新、backfill、品質チェックフック（quality モジュール呼び出し想定）の設計
    - _get_max_date 等のユーティリティによる既存データ確認
    - data.etl で ETLResult を再エクスポート

- リサーチ（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - momentum: 1M/3M/6M リターン、200日 MA 乖離の算出（営業日ベースのウィンドウ）
    - volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - value: raw_financials を用いた PER・ROE の算出（最新財務レコードを target_date 以前で取得）
    - DuckDB を用いた SQL + Python 実装、データ不足時は None を返す設計
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランク処理）
    - rank: ランク変換（round による丸めで ties を安定化）
    - factor_summary: count/mean/std/min/max/median の統計サマリー
  - research パッケージの公開関数を __all__ で整備（zscore_normalize は外部モジュールからインポート）

Internal / 設計方針（注記）
- ルックアヘッドバイアス防止: datetime.today()/date.today() をスコア計算内で直接参照しない設計（target_date を明示的に指定）
- DB 書き込みは冪等性を重視（DELETE→INSERT 等）し、部分失敗時に他データを保護
- OpenAI API 呼び出しは JSON Mode を想定し堅牢にパース・検証、異常時はフォールバックして例外を送出しない（フェイルセーフ）
- DuckDB 互換性を考慮（executemany の空リスト制約等）
- テスト容易性: OpenAI 呼び出しポイントは内部関数をモック可能に設計（unittest.mock.patch を想定）

Fixed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes
- OpenAI 関連機能は実行に API キー（OPENAI_API_KEY）を必要とします。その他、設定で必要な環境変数は settings のプロパティ参照を参照してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
- 実際の J-Quants クライアント（jquants_client）や quality モジュール、DB スキーマ等は別途提供されることを想定しています。

今後
- strategy / execution / monitoring サブパッケージの実装・発展
- ファクターセットの追加・チューニング、AI プロンプトやモデルの改良
- 長期的な品質チェックルールの拡充と監査ログ機能の強化

--- 
（この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴がある場合はコミット単位での更新を推奨します。）