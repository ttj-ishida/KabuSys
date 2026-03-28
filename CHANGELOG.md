# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

なお、この CHANGELOG はリポジトリの現行コードベースから推測して作成した初期リリース向けの記録です。

## [Unreleased]

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パブリック API のエントリポイントを定義（src/kabusys/__init__.py）。
  - モジュール群を公開: data, research, ai, config, など。

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースの強化:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート有無での振る舞いを区別）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須変数のチェック（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH の既定値を用意。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証ロジック。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データプラットフォーム関連（src/kabusys/data）
  - ETL パイプラインの表現（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを定義して ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約。
    - 差分取得、バックフィル、品質チェックの運用方針を実装想定（jquants_client と quality モジュールと連携）。
    - DuckDB を想定したユーティリティ関数（テーブル存在確認、最大日付取得など）。
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。
    - market_calendar を参照した営業日判定 API を提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 未取得時は曜日ベースのフォールバック（週末除外）を採用。
    - バックフィル、先読み、健全性チェック（未来日付の異常検出）を実装。
  - ETL インターフェース再エクスポート（src/kabusys/data/etl.py）

- リサーチ（研究）機能（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）
    - Volatility / Liquidity: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損のとき None）、ROE（raw_financials から取得）
    - DuckDB SQL を用いた一括計算、欠損時の None 扱い
  - 特徴量探索・統計（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応
    - IC（Information Coefficient、スピアマンランク相関）計算（calc_ic）
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクで処理
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算
  - research パッケージで関数群を __all__ で公開（zscore_normalize 再利用含む）

- AI（LLM）統合（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - 課題対策:
      - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
      - バッチサイズ（_BATCH_SIZE=20）で複数銘柄を同時評価。
      - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
      - レスポンスバリデーション（JSON 抽出・results フィールド・型チェック・未知コードの無視等）。
      - スコアは ±1.0 にクリップ。
      - DuckDB executemany の互換性考慮（空リスト送信を回避）。
    - パブリック API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - 時間ウィンドウ計算 calc_news_window（JST基準の前日15:00〜当日08:30に対応）を実装。
    - API 呼び出しはテスト時に差し替え可能な内部関数を用意。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロニュース抽出はニュース NLP の窓計算を利用（calc_news_window）。
    - ルックアヘッドバイアス対策: target_date 未満のデータのみを使用し、datetime.today() を参照しない実装。
    - LLM 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - パブリック API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。

- 実装上の堅牢性・運用上の配慮
  - lookahead bias 回避: 多くの関数で datetime.today()/date.today() を直接参照しない設計（外部から target_date を注入）。
  - DB 書き込みは冪等性を考慮（DELETE してから INSERT、トランザクション管理、ROLLBACK ログ）。
  - LLM レスポンスの不正・パース失敗や API エラーに対しては例外を上位へ波及させず、フェイルセーフでの継続やログ出力により堅牢化。
  - 詳細なログ出力（logger を利用）で運用時の診断を容易に。

### 変更 (Changed)
- 初回公開のため該当なし（初期実装）。

### 修正 (Fixed)
- 初回公開のため該当なし（初期実装）。

### 削除 (Removed)
- 初回公開のため該当なし（初期実装）。

### 既知の注意点 (Notes)
- OpenAI API（gpt-4o-mini）や DuckDB、J-Quants クライアントなど外部依存が必要です。実行環境に適切な環境変数（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）を設定してください。
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
- DuckDB のバージョン依存（executemany に空リストを渡せない等）を考慮した対策を実装していますが、運用環境の DuckDB バージョンでの動作確認を推奨します。
- AI モジュールのテスト容易性のため、内部 API 呼び出し関数はパッチ可能（unittest.mock.patch）に設計されています。

---

（この CHANGELOG はコード内容からの推測に基づく初期リリース記録です。実際のリリースノートやリポジトリの履歴と差異がある場合は、適宜更新してください。）