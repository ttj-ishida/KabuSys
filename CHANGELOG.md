# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

---

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買プラットフォーム（KabuSys）の基礎機能群を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パブリックモジュールエクスポート: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定管理 (kabusys.config)
  - Settings クラスを導入し、環境変数経由で各種設定を取得可能に。
  - .env / .env.local 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env パーサー実装:
    - コメント行 / export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理。
    - ファイル読み込み失敗時の警告発行。
    - 自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値（割合）
    - KABUSYS_ENV (development|paper_trading|live) と LOG_LEVEL のバリデーション
    - ヘルパー: is_live, is_paper, is_dev

- データプラットフォーム（kabusys.data）
  - 市場カレンダー管理モジュール (calendar_management)
    - market_calendar を使った営業日判定ロジック: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DBデータがない場合の曜日ベースフォールバック
    - calendar_update_job: J-Quants からカレンダー差分取得・冪等保存（バックフィル・健全性チェック含む）
  - ETL パイプライン基盤 (pipeline, etl)
    - ETLResult データクラスによる実行結果集約（品質チェック結果やエラーの収集を含む）
    - pipeline モジュールの型再エクスポート (ETLResult)
    - 差分取得・バックフィル・品質チェックを想定した設計（DataPlatform.md 準拠）

- AI / ニュース NLP (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）へ送信
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数上限（過剰トークン対策）
    - JSON Mode を期待したレスポンス検証（復元ロジック含む）、レスポンスバリデーション、スコア ±1.0 にクリップ
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ
    - 部分失敗に備えた冪等的な DB 書き込み（該当 code の DELETE → INSERT）
    - テスト用に OpenAI 呼び出しをモック差し替え可能（_call_openai_api）
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計
  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
    - マクロニュース抽出（キーワードフィルタ）と LLM によるセンチメント評価
    - LLM 呼び出しに対するリトライ・フォールバック（失敗時 macro_sentiment=0.0）
    - 最終結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - OpenAI クライアントの注入とテスト差替えポイントあり

- 研究・ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（データ不足時の扱い）
    - ボラティリティ/流動性: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
    - バリュー: PER、ROE（raw_financials からの最新財務データを使用）
    - DuckDB を使った SQL 集約＋Python の組合せで実装
  - feature_exploration:
    - 将来リターン計算（任意 horizon、入力検証、1/5/21 日がデフォルト）
    - IC（Information Coefficient）計算（Spearman 的ランク相関、必要件数チェック）
    - ランク関数（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）
    - pandas 等に依存しない純標準ライブラリ実装

- テスト・堅牢性関連
  - OpenAI 呼び出しのテスト差替えポイントを各モジュールに提供（_call_openai_api を patch 可能）
  - API レスポンスの堅牢なパースと不正レスポンス時のフォールバック（例外を上げずログに落として継続）
  - DuckDB の executemany に対する空リスト制約に対応する保護ロジック（空時は実行しない）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- OpenAI API キーは各関数の api_key 引数または環境変数 OPENAI_API_KEY で解決されます。未設定時は ValueError を送出します。
- DuckDB を前提に実装されているため、実行には適切なスキーマ/テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等）の準備が必要です。
- ロギング／例外ハンドリングは意図的に保守性・安全性を重視した設計（失敗を全面停止させず、部分結果を保護しつつ進行）となっています。