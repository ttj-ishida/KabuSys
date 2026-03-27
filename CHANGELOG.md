# Change Log

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/) の形式に従っています。  
このファイルは、提供されたコードベースの内容から推測して作成した初期の変更履歴です（実際のコミット履歴がないため実装内容を基に要約しています）。

## [0.1.0] - 2026-03-27
初回リリース（推定）。主要機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは 0.1.0。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に登録。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git / pyproject.toml に基づく）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - export KEY=val 形式やクォート・エスケープ、コメント扱いなどを考慮した独自パーサを実装。
  - 必須設定の取得用 Settings クラスを実装（J-Quants, kabu API, Slack, DB パス, ログレベル等）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と is_live / is_paper / is_dev プロパティを提供。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・1銘柄あたりの最大記事数 / 最大文字数トリム、スコアを ±1.0 にクリップ。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフによるリトライ実装。
    - レスポンスのバリデーション（JSON抽出、results 配列、code の正規化、数値検査）。
    - スコアの idempotent な DB 書き換え（対象コードのみ DELETE → INSERT）を実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを提供（テスト/再現性のため datetime.today() を参照しない設計）。
    - テスト容易性のため _call_openai_api を patch 可能に実装。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）、レスポンスパース、スコア合成、閾値によるラベリングを実装。
    - API のリトライ / フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK ハンドリング。
    - テスト用に _call_openai_api を patch 可能に実装し、news_nlp と意図的に内部関数を共有しない設計。

- データ基盤 (src/kabusys/data)
  - ETL パイプライン用データクラス ETLResult（src/kabusys/data/pipeline.py）を追加し、ETL 実行結果や品質チェックの集約を提供。
  - ETL ユーティリティの公開インターフェースを etl.py で再エクスポート。
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - J-Quants からの夜間バッチ更新 job (calendar_update_job) を実装（バックフィル、健全性チェック、差分取得）。
    - DB 未取得領域では曜日ベースのフォールバックを採用して堅牢化。
    - _MAX_SEARCH_DAYS 等の安全措置を導入。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の SQL ウィンドウ関数で計算する機能を追加。
  - feature_exploration.py: 将来リターン計算（複数 horizon 対応）、IC（スピアマンランク相関）計算、ランク関数、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージの __init__ で主要関数を公開し、data.stats の zscore_normalize を再利用。

### 変更 (Changed)
- 設計方針の一貫性
  - 多くのモジュールで「ルックアヘッドバイアス防止」のために datetime.today()/date.today() を内部で参照しない設計を採用（target_date を明示的引数とする）。
  - DuckDB を主要なローカル分析用 DB として採用。SQL と Python を組み合わせて処理を実装。

- エラー処理／ロギング
  - OpenAI API 呼び出し周りにリトライ戦略を導入し、失敗時は例外を投げずフェイルセーフ（0 相当）で継続する箇所を明確化（サービス継続性重視）。
  - DB 書き込みはトランザクションを用いて冪等性を確保、失敗時は ROLLBACK を試行して詳細ログを出力。

### 修正 (Fixed)
- レスポンスパースの堅牢化
  - OpenAI JSON Mode の結果でも前後に余計なテキストが混入するケースを想定し、最外側の {} を抽出して復元するロジックを追加（news_nlp の _validate_and_extract 等）。

- 型・境界チェック
  - 各モジュールで None / 非有限値 / 空パラメータに対する防御的チェックを追加（スコアクリップ、数値変換、安全な DB executemany のための空チェック等）。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API 依存
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini）に依存。api_key 注入は引数または OPENAI_API_KEY 環境変数を利用する必要がある。未設定時は ValueError を送出する。
- DuckDB 依存の挙動
  - executemany に空リストを渡せない環境 (例: DuckDB 0.10) を考慮して空チェックを導入している。実行環境の DuckDB バージョンにより挙動が異なる可能性がある。
- テスト容易性
  - OpenAI 呼び出しはモジュール内で _call_openai_api を定義しており、ユニットテストでは patch で差し替え可能。ただしモジュール間で _call_openai_api は共有していない（意図的）。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし（今後のバージョンで API シグネチャや DB スキーマ変更がある場合は要注意）。

---

今後の追加候補（実装方針の提案）
- モニタリング / アラート: Slack 連携を用いた ETL / モデル異常通知機能のサンプル実装（Settings は Slack トークン・チャンネルを取得済み）。
- strategy / execution / monitoring の具体的実装: 今回の基盤に対して売買戦略・発注ラッパー・監視ダッシュボードを追加。
- CI / テスト: DuckDB のモックや OpenAI 呼び出しのモック化を用いた単体テストセットアップ例。
- ドキュメント: API キー・.env 例 (.env.example)、DB スキーマ定義、運用手順の追加。

（この CHANGELOG は提供されたコードの内容から推測して整理したものです。実際の変更履歴やリリースノートはリポジトリのコミットログを参照してください。）