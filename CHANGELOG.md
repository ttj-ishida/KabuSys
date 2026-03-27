# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期の変更履歴（リリースノート）です。

## [Unreleased]
（今後の変更記録用）

## [0.1.0] - 初回リリース
初回の機能実装。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主にデータ取得・ETL、マーケットカレンダー管理、ファクター計算、ニュース NLP / LLM を用いたセンチメント評価、および各種ユーティリティを含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) とバージョン定義（__version__ = "0.1.0"）。
  - モジュール公開 API の整理（data / research / ai / ...）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない挙動。
  - .env パーサーは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テストなどで利用可能）。
  - OS 環境変数を保護する仕組み（読み込み時に protected set を用いる）。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得：
    - J-Quants / kabuAPI / Slack / DB パス（DUCKDB_PATH/SQLITE_PATH）など。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションと is_live / is_paper / is_dev フラグ。

- ニュース NLP（AI） (kabusys.ai.news_nlp)
  - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する機能を実装。
  - 処理の特徴：
    - JST ベースのニュースウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供（UTC 変換して DB と比較）。
    - 1銘柄あたりの最大記事数・文字数トリム（トークン肥大化対策）。
    - 最大 20 銘柄ずつのバッチ処理（_BATCH_SIZE）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフを含む再試行。
    - レスポンスの厳密なバリデーション（JSON パース回復処理、results の形式チェック、スコア数値化、未知コードは無視）。
    - スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗時に既存スコアを保護する方式（対象コードのみ DELETE → INSERT）で冪等に実施。
    - テスト容易性のため OpenAI 呼び出し箇所は patch で差し替え可能（_call_openai_api）。

- 市場レジーム判定（AI + テクニカル） (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（"bull"/"neutral"/"bear"）を判定し market_regime テーブルへ書き込む機能を追加。
  - 特徴：
    - ma200 乖離の計算は target_date 未満のみを使用してルックアヘッドバイアスを回避。
    - マクロ記事抽出はニュースモジュールのウィンドウ計算を利用。
    - OpenAI 呼び出しには再試行・エラーハンドリングを実装し、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - スコア合成後はクリッピングして閾値でラベル付け。
    - DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターンで実施。失敗時には ROLLBACK を試行。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS が 0/欠損なら None）。
    - すべて DuckDB の SQL を活用（外部 API にはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: スピアマンのランク相関（IC）計算（欠損処理、最小レコード数チェックあり）。
    - rank / factor_summary: ランク変換、統計サマリー（count/mean/std/min/max/median）。
  - zscore_normalize を data.stats から再エクスポート。

- データ基盤 (kabusys.data)
  - calendar_management:
    - market_calendar ベースの営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェック（将来日付の異常検出）を実装。
  - ETL / pipeline:
    - ETLResult データクラスを提供（取得件数 / 保存件数 / 品質チェック結果 / エラー一覧 等）。
    - pipeline モジュールに基づく ETL の設計に対応するユーティリティを実装（差分取得、保存、品質チェックとの連携を想定）。
    - jquants_client を通じた API 取得 → save_* での冪等保存を想定（ON CONFLICT / upsert）。

- 汎用・設計方針（全体）
  - すべてのデータ処理でルックアヘッドバイアスを防ぐため、datetime.today()/date.today() を参照しない設計を推奨する箇所を明記。
  - OpenAI 呼び出しは両モジュールともに patch/差し替え可能に実装し、テスト容易性を考慮。
  - 外部ライブラリ（pandas 等）に依存せずに標準ライブラリ + DuckDB SQL で実装する方針。
  - ロギングとウォーニングが各所で充実（API失敗、データ不足、ROLLBACK 失敗などを通知）。

### 変更 (Changed)
- （初回リリースのため特記事項なし）

### 修正 (Fixed)
- （初回リリースのため特記事項なし）

### セキュリティ (Security)
- .env の読み込みに際して OS 環境変数を保護する仕組みを導入（override 時も protected set を除外）。
- OPENAI_API_KEY 未設定時は明確な ValueError を投げ、API キー管理ミスを早期検出。

### 既知の設計上の注意点 / TODO
- ai モジュールは OpenAI の JSON mode を前提としているため、API レスポンス形式の変化やモデルの振る舞い変更に注意。
- DuckDB executemany のバージョン互換性（空リストの扱い）に対する防御コードが含まれるため、DuckDB のバージョン差異を考慮のこと。
- 一部の機能（jquants_client, quality モジュールなど）は外部実装依存であり、実行環境に合わせた設定・実装が必要。

---

この CHANGELOG はリポジトリ内のソースコードから想定される機能と設計方針に基づいて作成しています。実際のリリースノートとして用いる場合は、変更の意図や日付、関連するチケット番号等を追記してください。