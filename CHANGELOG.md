# CHANGELOG

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムのコア機能セットを実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) とバージョン定義: __version__ = "0.1.0"。
  - モジュール公開: data, strategy, execution, monitoring（__all__）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数読み取り用 Settings クラスを提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の利便性プロパティ
  - OS 環境変数は保護（.env の上書き制御）。

- AI（自然言語処理）機能 (src/kabusys/ai)
  - news_nlp.score_news
    - raw_news と news_symbols を使って銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC 変換を行う calc_news_window を提供）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、トリム（記事数/文字数制限）や JSON Mode を利用したレスポンスバリデーションを実装。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。
    - レスポンス検証で不正な応答はスキップし、部分成功時は既存データ保護のため対象銘柄のみ DELETE → INSERT。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とニュース由来のマクロセンチメントを合成して日次の市場レジーム（bull／neutral／bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
    - マクロニュースは raw_news からキーワードフィルタで抽出し、OpenAI（gpt-4o-mini）により JSON 出力で macro_sentiment を取得。
    - 合成重み: MA70% / Macro30%、スコアはクリップ（-1～1）、閾値でラベル振り分け（BULL_THRESHOLD / BEAR_THRESHOLD）。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。

- データプラットフォーム（Data）機能 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を利用した営業日判定とユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーが無い場合は曜日ベース（土日休業）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックあり）。
  - ETL パイプライン（pipeline.py）
    - DataPlatform に準拠した ETLResult dataclass を実装（取得数／保存数／品質問題／エラー等を保持）。
    - 差分取得、バックフィル、品質チェックの設計に対応する内部ユーティリティを実装（テーブル存在確認、最大日付取得等）。
  - etl モジュールで ETLResult を再エクスポート（data/etl.py）。
  - jquants_client など外部データクライアントは想定（コード内で参照）。

- リサーチ（研究）機能 (src/kabusys/research)
  - factor_research.py
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200日 MA 乖離算出。
    - ボラティリティ・流動性 (calc_volatility): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - バリュー (calc_value): raw_financials と株価から PER / ROE を算出（EPS=0 / 欠損時は None）。
    - すべて DuckDB の SQL を用いた実装（外部 API 呼び出しなし）。欠損時の取り扱いやデータ不足に対する None 戻りを明示。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、ホライズン検証あり）。
    - IC（Information Coefficient）calc_ic（スピアマンのランク相関）。
    - ランク付けユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research/__init__.py で主要関数を再エクスポート。

- 共通設計・実装上の配慮
  - ルックアヘッドバイアス回避: datetime.today() / date.today() を直接扱わず、target_date 引数ベースで計算する設計を採用。
  - DuckDB を中心に SQL と Python の組合せで高効率に集計・計算を行う。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化、例外時は ROLLBACK を行う。
  - OpenAI 呼び出しは堅牢にリトライ設計（429/ネットワーク/5xx など）でフェイルセーフを提供。
  - ロギングを広く導入し、失敗や異常時には警告/例外ログを出力する設計。

### 修正 (Fixed)
- なし（初回リリースのため過去のバグ修正履歴はありません）。

### 破壊的変更 (Removed / Deprecated)
- なし（初回リリース）。

### 既知の制限 / 注意事項
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用する必要あり。未設定時は ValueError を発生させる実装。
- research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存する。テーブルスキーマが期待通りでない場合はエラーとなる可能性がある。
- news_nlp / regime_detector は gpt-4o-mini を利用する前提のプロンプト設計を行っている（モデルやレスポンス形式の変更はプロンプト/検証ロジックの更新が必要）。
- 一部の executemany 呼び出しは DuckDB のバージョン差異を考慮して空リスト回避の分岐を実装している（互換性対策）。

---

今後の予定（例）
- strategy / execution / monitoring の具体的な戦略実装や発注ロジックの追加
- テストカバレッジの拡充と CI 連携
- J-Quants / kabu API クライアントの抽象化とリトライ強化
- モデルやプロンプト改善、LLM 呼び出しの可観測性向上

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は差分確認を行ってください。）