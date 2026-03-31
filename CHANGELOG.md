# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初期リリース。

### 追加 (Added)
- パッケージ初期実装: kabusys (日本株自動売買支援ライブラリ)
  - パッケージメタ情報: version = 0.1.0、公開モジュール: data, research, ai, execution, monitoring（__all__ により宣言）
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env の柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）
  - OS 環境変数を保護する protected オプション（.env.local は上書き可能だが既存 OS 環境変数は保持）
  - Settings クラスによる明示的な環境変数アクセス API（必須変数チェック、デフォルト値、バリデーション）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック（開発 / ペーパートレード / 本番（live） 等）
    - データベースファイルパス設定（DUCKDB_PATH / SQLITE_PATH）

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を用いたニュースの銘柄別集約と OpenAI によるセンチメント付与機能
  - ニュース時間ウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）
  - バッチ処理（1 API コールで最大 20 銘柄）、1 銘柄あたりの記事数・文字数上限（デフォルト: 10 件 / 3000 文字）
  - gpt-4o-mini を JSON Mode で呼び出し、厳密な JSON レスポンスを想定
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ (最大リトライ回数設定)
  - レスポンスの堅牢なバリデーションとスコアクリップ（±1.0）
  - 部分成功の際に既存スコアを保護するための置換ロジック（DELETE → INSERT、対象コードに限定）
  - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す
  - テスト容易性考慮: OpenAI 呼び出し点を内部関数として差し替え可能

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
  - マクロニュースはニュース NLP のウィンドウ選定機能を流用し、マクロキーワードでフィルタ
  - OpenAI 呼び出しは独立実装（モジュール結合を避ける設計）
  - フェイルセーフ: API 失敗時は macro_sentiment=0.0 として継続
  - 冪等な DB 書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）
  - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す

- データ基盤ユーティリティ（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar を基にした営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）
    - DB にカレンダーがない場合は曜日（週末）ベースのフォールバック
    - calendar_update_job により J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）
  - ETL パイプラインの公開インターフェース（pipeline.ETLResult を data.etl 経由で再エクスポート）
  - ETLResult データクラス（ETL 実行結果の集約、品質問題のシリアライズ等）
  - pipeline モジュール: 差分更新、バックフィル、品質チェック連携のためのユーティリティ関数（DB 最大日取得等）

- リサーチ（kabusys.research）
  - ファクター計算 (research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時の None 扱い）
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率
    - calc_value: raw_financials を用いた PER / ROE（EPS が 0/欠損 の場合は None）
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns: 将来リターン（任意ホライズン）を一回のクエリで計算
    - calc_ic: Spearman（ランク相関）による IC 計算（有効レコード不足時は None）
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸め処理で ties 対応）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー
  - 研究用途の設計方針: DuckDB と標準ライブラリのみで実装、実際の発注等には無関係

### 修正 (Fixed)
- .env パーサの改善
  - 引用符内のバックスラッシュエスケープ処理、インラインコメントやクォート閉じ位置の正確な解析を実装
  - export プレフィックスやコメントの扱いに対応
- OpenAI レスポンス処理の堅牢化
  - JSON Mode でも前後に余計なテキストが混入するケースに対する最外側の {} 抽出による復元処理を追加
  - レスポンスバリデーションで未知コードや非数値スコアを無視することで部分的不整合に耐える実装に
- DuckDB 関連の互換性考慮
  - executemany に空リストを渡さない保護（DuckDB 0.10 の制約への対応）
  - テーブル存在チェックや日付カラムの最大値取得で robust な型処理を実装

### 変更 (Changed)
- 設計上の注意点を明文化
  - ルックアヘッドバイアス防止のために datetime.today() / date.today() に依存しない実装方針を各モジュールで採用
  - 外部 API 呼び出し失敗時はフェイルセーフ（継続）する設計を統一的に適用

### 既知の制限 (Known Issues)
- OpenAI（gpt-4o-mini）への依存
  - API 利用のためのキー（OPENAI_API_KEY）が必須。テスト時は呼び出し関数をモックすることを推奨。
- jquants_client の実体実装は参照しているが（fetch / save 処理）、この変更履歴作成時点のコードベースに含まれる詳細実装に依存するため、利用時は該当クライアントの動作確認が必要。
- 一部の DB スキーマ（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, news_symbols 等）の事前準備が必要。

### セキュリティ (Security)
- API キーは環境変数で管理する設計（Settings クラスで必須チェック）。誤って .env を公開しない運用上の注意が必要。
- .env 読み込み順序: OS 環境 > .env.local > .env（.env.local は上書きだが OS 環境変数は保護）

---

注: 本 CHANGELOG は提供されたコードの内容から推測して作成した概要です。実際のリリースノートとして公開する際は、テスト対象や実装差分（コミット履歴）に基づいた補正・追記を行ってください。