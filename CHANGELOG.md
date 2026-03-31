# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、セマンティック バージョニングを利用しています。  
このファイルはコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-31 (Initial release)

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。モジュール公開一覧として data, strategy, execution, monitoring を __all__ に設定。

- 設定管理
  - 環境変数/.env 管理モジュールを実装（src/kabusys/config.py）。
    - .env および .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（OS 環境変数優先、.env.local は上書き）。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パース機能はコメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応。
    - protected パラメータにより既存 OS 環境変数を上書きしない保護ロジックを実装。
    - Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等のプロパティを提供）。
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ受け入れ、LOG_LEVEL は標準的なログレベルを検証。

- AI（自然言語処理）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols テーブルのデータを銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB を検索）。
    - 1チャンクで最大20銘柄、1銘柄あたり最大10記事・3000文字にトリムすることでトークン肥大を抑制。
    - レート制限(429)、ネットワーク切断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" 配列、code と score チェック、既知コードのみ採用、スコアは ±1.0 にクリップ。
    - DB 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）。DuckDB の executemany 空リスト制約に対応。
    - テスト補助: OpenAI 呼び出し部を差し替え可能（unittest.mock.patch 対応）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）の線形合成で日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - マクロキーワードによる raw_news フィルタリング（最大 20 件）を実施し、OpenAI（gpt-4o-mini）で macro_sentiment を取得。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レート制限・ネットワーク等のエラーに対してリトライを行う。ローカル関数で API 呼び出しを実装しモジュール間の結合を避ける。
    - DuckDB を用いた冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。

- データ処理（Data）
  - ETL パイプラインのインターフェース（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを提供（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（J-Quants クライアント経由でデータ取得・保存）。
    - DuckDB のテーブル存在チェックや最大日付取得のユーティリティを実装。

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・探索ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB データがない場合は曜日ベース（平日＝営業日）でフォールバック。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
    - ループ上限（_MAX_SEARCH_DAYS）を設け無限探索を防止。

- リサーチ（研究用モジュール）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（欠損処理を考慮）。
    - バリュー: raw_financials から EPS/ROE を取得して PER/ROE を計算。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に算出。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズンをサポート、horizons 引数で検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、有効レコード 3 件未満は None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
    - 外部依存を避け、標準ライブラリと DuckDB のみで実装。

### 変更点 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは必須（関数引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出して処理を中止。
- .env の自動読み込みは既存 OS 環境変数を保護（protected set）し、.env.local は上書きの順で読み込む設計。自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- 重要な機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings 経由で明示的に取得し、未設定時はエラーを出す（早期検出）。

### 設計上の注意・既知の制約 (Notes / Known limitations)
- ルックアヘッドバイアス回避: date.today() や datetime.today() を直接参照せず、すべての処理は呼び出し側から渡される target_date に基づいて行われる設計。
- API 呼び出し失敗時は「スキップ」または「フェイルセーフ値（例: macro_sentiment=0.0）」で継続する設計。つまり一部結果が欠ける可能性があるが処理全体を停止しないことを優先している。
- DuckDB のバージョン・仕様差異（例: executemany の空リストバインド動作）を考慮した実装上の対処あり。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有していない（テストの差し替えを想定）。
- 実際の発注（execution）やモニタリング機能の実装詳細はこのリリースのコード一覧の中に含まれていない（パッケージの公開モジュールには含むが、今回提供されたコードスニペットでは詳細未記載）。

---

今後のリリースでは、テストカバレッジ、エンドツーエンドの ETL ワークフロー、monitoring/strategy/execution の実装拡充、より詳細なドキュメント（操作手順、データベーススキーマ、J-Quants/Slack/Kabu API の統合手順）を追記予定です。