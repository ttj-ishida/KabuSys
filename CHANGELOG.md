# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: このリリースノートはコードベースから推測して作成しています。実際の変更履歴やリリースノート作成ポリシーに合わせて適宜編集してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回公開リリース

### 追加 (Added)
- パッケージの基本構造を追加
  - パッケージ名: kabusys
  - パッケージ版: 0.1.0
  - パブリックサブパッケージ: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート
  - .env ファイルのパース機能を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）
  - 環境変数保護（OS 環境変数を protected として .env.local の上書きを制御）
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目の取得と未設定時の ValueError を提供
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス提供
    - KABUSYS_ENV のバリデーション (development / paper_trading / live)
    - LOG_LEVEL のバリデーション (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - is_live / is_paper / is_dev の利便性プロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出する機能を実装（score_news）
  - 特徴
    - 前日 15:00 JST ～ 当日 08:30 JST を対象とするウィンドウ計算（calc_news_window）
    - 1 銘柄あたり最大記事数 / 最大文字数でトリム（トークン肥大対策）
    - 最大 20 銘柄を 1 チャンクとしてバッチ送信（_BATCH_SIZE）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行
    - API レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・型チェック、未知コードの無視、数値チェック）
    - スコアは ±1.0 にクリップ
    - 取得済みコードのみを対象に ai_scores テーブルを「DELETE → INSERT」で冪等更新
    - API キーは引数または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定する機能を実装（score_regime）
  - 特徴
    - ma200_ratio の計算（target_date 未満のデータのみ使用、データ不足時は中立 1.0）
    - マクロキーワードによる raw_news タイトル抽出（最大 20 記事）
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを算出、API 失敗時は macro_sentiment = 0.0 にフォールバック
    - レジームスコア合成と閾値判定（_BULL_THRESHOLD / _BEAR_THRESHOLD）
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、障害時は ROLLBACK）

- リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算。データ不足時は None を返す。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS が 0 または欠損なら None）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン先の将来リターン（デフォルト [1,5,21]）を一括クエリで計算
    - calc_ic: スピアマン（ランク）相関による IC 計算（有効レコード < 3 の場合は None）
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め対策あり）
    - factor_summary: count/mean/std/min/max/median の統計サマリー算出
  - zscore_normalize を kabusys.data.stats から再エクスポート

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ロジックを提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先、未登録日は曜日ベースでフォールバック
    - 最大探索範囲制限(_MAX_SEARCH_DAYS) による安全化
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等保存（バックフィル・健全性チェックあり）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（ターゲット日・取得/保存件数・品質問題・エラーの集約）
    - 差分取得、保存（jquants_client 経由）、品質チェック（quality モジュールとの連携）を想定した設計
    - _get_max_date / _table_exists 等のユーティリティ
  - etl モジュールは pipeline.ETLResult を再エクスポート

- DuckDB を想定した SQL 実装
  - 各種集計・ウィンドウ関数・executemany の扱い（DuckDB 互換性考慮）を反映

### 修正 / 安全対策 (Fixed / Hardening)
- API 呼び出しに対するフォールバック動作を統一
  - OpenAI API の一時的障害や 5xx、タイムアウト時は再試行とログ出力を行い、全リトライ失敗時は 0.0（中立）で継続（例外を上げずフェイルセーフ）
  - JSON パース失敗やバリデーション失敗時は該当チャンクをスキップし、他の処理は継続
- データ不足時の安全な既定値設定
  - ma200_ratio 等でデータ不足時は 1.0（中立）を返す
  - ファクター計算でウィンドウに不足がある場合は None を返す
- DB 書き込みでのトランザクション保護
  - BEGIN / DELETE / INSERT / COMMIT を使用し、例外時は ROLLBACK を試行。ROLLBACK 失敗時は警告ログを記録
  - ai_scores 書き込みは取得済みコードのみ置換して部分失敗時の既存データ保護を実現
  - DuckDB executemany の空リストに対する互換性対策（空の場合は実行しない）

### ドキュメント / 設計コメント (Documented)
- 各モジュールに詳細な docstring を追加し、処理フロー・設計方針・フェイルセーフ挙動を明記
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計指針を明示
  - OpenAI 呼び出しはテスト用に _call_openai_api をモック可能に設計
  - プロンプト設計（SYSTEM_PROMPT）および JSON mode 出力の前提を明記

### 既知の動作・注意点 (Notes)
- OpenAI API キー（OPENAI_API_KEY）や各種トークン系環境変数は必須（Settings が未設定時に ValueError を発生）
- .env の自動読み込みはプロジェクトルート探索に依存するため、パッケージ配布後に利用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や明示的な設定が必要
- news_nlp / regime_detector は gpt-4o-mini を前提としており、レスポンスの形式が変わるとバリデーションでスキップされる可能性がある
- DuckDB のバージョン差と executemany の挙動に配慮した実装（空パラメータでの実行を避ける）

---

今後の予定（例）
- strategy / execution / monitoring の実装充実（現状はパッケージ構造のみ）
- テスト用のモッククライアントの整備とユニットテストの追加
- OpenAI 呼び出しの抽象化によるモデルの切替容易化

（以上）