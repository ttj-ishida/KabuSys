# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初回公開バージョンの変更点をコードベースから推測して記載しています。

## [0.1.0] - 2026-04-03

初期リリース — KabuSys: 日本株自動売買 / データ基盤 / 研究・解析・AI支援モジュール群を含むパッケージ。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 kabusys を追加。公開 API として data, research, ai, execution, monitoring, strategy 等を想定したモジュール群をエクスポート。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。  
    - 読み込み優先度: OS 環境変数 > .env.local > .env。  
    - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート。
  - .env のパース機能を独自実装（export KEY=val 形式、クォート内のエスケープ、コメント処理等に対応）。
  - Settings クラスを実装し、環境変数をプロパティ経由で安全に取得：
    - 必須変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を _require で検証）。
    - オプションやデフォルト値（KABU_API_BASE_URL, LINE_* トークン、DB パス等）を提供。
    - システム環境: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
    - 監視関連設定（PID ファイルパス、kill flag、CPU/Memory/Disk の閾値）をプロパティとして提供。

- データプラットフォーム: カレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar テーブルに基づく営業日判定ロジックを提供：
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB に値がない場合は曜日ベース（土日を休日扱い）のフォールバックを採用。
    - 最大探索日数を設定して無限ループを回避（_MAX_SEARCH_DAYS）。
  - 夜間バッチ更新 job: calendar_update_job を実装（J-Quants API クライアント経由で差分取得・冪等保存、ルックアヘッド・バックフィル・健全性チェックあり）。

- データ ETL パイプライン (src/kabusys/data/pipeline.py, etl.py)
  - ETLResult データクラスを公開（ETL 実行メタ情報、品質問題、エラー情報を保持）。
  - 差分更新・バックフィルの方針を取り入れた ETL 設計（J-Quants クライアント連携、品質チェック集約）。
  - デフォルト設定（最小データ日、カレンダー先読み、バックフィル日数等）を定義。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini, JSON mode) を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
    - 特徴:
      - JST ベースのタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC 日時へ変換して DB 検索。
      - 1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大化対策）。
      - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
      - リトライ戦略（429/ネットワーク/タイムアウト/5xx を指数バックオフで再試行）、レスポンス検証、スコアのクリップ処理、部分成功時に既存スコアを保護する更新ロジック（DELETE → INSERT）。
      - テスト用に _call_openai_api をモック可能に設計。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - 特徴:
      - ma200_ratio の計算は target_date 未満のデータのみ使用してルックアヘッドを防止。
      - マクロニュースは news_nlp.calc_news_window を使って収集。記事がない場合は LLM を呼ばず macro_sentiment = 0.0。
      - OpenAI 呼び出しはリトライとエラー分類を実装。API 失敗時はフェイルセーフで neutral 方向へ寄せる挙動（macro_sentiment=0.0）。
      - gpt-4o-mini を使用し、レスポンスは JSON モードで受け取りパースする設計。
  - ai.__init__ で score_news を公開。

- 研究・因子解析モジュール (src/kabusys/research)
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB 接続を受け SQL クエリで計算）。
    - モメンタム、200 日移動平均乖離、ATR、流動性（出来高・売買代金）、PER/ROE 等を計算。データ不足時は None を返す設計。
  - feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターンを一括で計算）、calc_ic（スピアマンランク相関＝IC）、rank（同順位は平均ランクで処理）、factor_summary（基本統計量）を実装。
    - 外部依存を避け、標準ライブラリと DuckDB のみで処理。
  - research.__init__ で主要関数と zscore_normalize を再エクスポート。

- 実装上の堅牢性/運用配慮
  - DuckDB を主体とした SQL 実装（テーブルスキーマ前提）。空リストでの executemany の扱い等、DuckDB 固有制約に配慮した実装。
  - API 呼び出し（OpenAI / J-Quants）に対してはリトライ/バックオフ・パース検証・フェイルセーフを導入し、部分失敗時のデータ保全を優先。
  - ルックアヘッドバイアス対策として、date.today()/datetime.today() を各スコア関数で直接参照しない設計を採用（target_date を明示的に受け取るインタフェース）。

### 変更 (Changed)
- 初版のため該当なし（新規追加）。

### 修正 (Fixed)
- 初版のため該当なし（新規追加）。

### 破壊的変更 (Removed)
- 初版のため該当なし（新規追加）。

### セキュリティ (Security)
- OpenAI/API キーや Kabu API のパスワード等の秘密情報は環境変数を通じて設定する設計。`.env.local` が `.env` より優先される点に注意。
- 環境変数読み込みはデフォルトで自動実行されるため、CI/テスト環境で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すること。

### 既知の制限 / 注意事項 (Known issues / Notes)
- 各モジュールは DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar 等）の存在を前提としている。テーブル定義/マイグレーションは本パッケージに含まれていないため、別途準備が必要。
- OpenAI の呼び出しは openai.OpenAI クライアントを使用する想定。API のバージョン変化やレスポンス仕様の変更があった場合、パースロジックの修正が必要になる可能性がある。
- news_nlp と regime_detector は JSON Mode を前提としたパースを行うが、稀に余計なテキストが混入する場合に備えた救済処理（最外側の {} を抽出）を実装している。完全な堅牢性は保証されない。
- ETL / calendar_update_job / jquants_client の詳細な振る舞い（API レート制限、認証フロー等）は jquants_client 実装依存。J-Quants 連携用の refresh token などは設定が必要。
- tests 向けに OpenAI 呼び出し関数をモック可能な設計になっている（_call_openai_api を patch）。

---

今後の予定（例）
- 監視 / 実行（execution, monitoring）モジュールの充実（実売買フロー・オーダ管理・プロセス監視等）。
- ドキュメント強化（テーブルスキーマ、運用手順、設定例）。
- テストカバレッジ拡張と CI 統合。