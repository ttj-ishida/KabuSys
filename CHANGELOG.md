# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に従います。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-03

初回公開リリース。以下の主要機能と設計方針を実装しています。

### 追加 (Added)

- パッケージ基礎
  - パッケージ名: kabusys。バージョン: 0.1.0。
  - 主要サブパッケージを公開: data, research, ai, execution, monitoring, strategy（__all__ により公開）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存、配布後に安定）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサー実装: export 文対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いに配慮。
  - 重要環境変数取得ヘルパ: Settings クラスを提供（例: settings.jquants_refresh_token, settings.kabu_api_password）。
  - 設定検証:
    - KABUSYS_ENV は development / paper_trading / live のみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - 各種デフォルト値:
    - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PID / KILL フラグファイルパス等、監視用設定と閾値（CPU/MEM/DISK）を環境変数で調整可能。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理と営業日判定ユーティリティを提供。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - market_calendar が未登録のときは曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar に冪等保存。バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得件数・保存件数・品質問題・エラー集約）。
    - 差分取得・保存・品質チェックの設計方針を反映（idempotent 保存、backfill、品質問題は収集して呼び出し元で判断）。
  - jquants_client と連携する想定の設計（fetch/save 呼び出し箇所、例外ハンドリングを実装）。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - raw_news + news_symbols を元に銘柄別に記事を集約し OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ送信（チャンクサイズ: 20 銘柄）、1銘柄あたり最大記事数 10、最大文字数 3000 でトリム。
    - JSON Mode 出力の検証・正規化ロジックを実装（余分な前後テキストから最外の {} を抽出する耐性あり）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ。その他はスキップ（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保持するため、対象コードのみ DELETE → INSERT。
    - テスト容易性: _call_openai_api をモック差し替え可能。
  - regime_detector:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - 設定: MA スケール係数、重み、閾値（bull/bear = 0.2）などを定数化。
    - マクロニュース抽出はキーワードベース（デフォルトセットあり）、最大取得記事数 20。
    - OpenAI 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試みエラーを伝播。
    - ルックアヘッドバイアス対策: target_date ベースで date 未満のみを参照（datetime.today() を参照しない）。
    - テスト容易性: news_nlp と独立した _call_openai_api 実装。
  - 共通設計:
    - 共に OpenAI の gpt-4o-mini を使用、JSON Mode 利用、応答のバリデーションとクリップ等を実装。
    - API レスポンスのパース失敗や API エラーに対するログ出力と安全なフォールバックを徹底。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）などを DuckDB の SQL と Python で計算。
    - データ不足時の None 処理、営業日ベースの窓設計、スキャンバッファ採用（例: momentum 用スキャン 400 日）を実装。
    - 各関数は prices_daily / raw_financials のみ参照し本番口座へのアクセスはしない設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman の ρ）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズン（1/5/21 日等）に対応、horizons のバリデーション（正の整数かつ <=252）あり。
    - rank は同順位を平均ランクで扱い、浮動小数の丸め（round(v,12)）で ties の検出漏れを防止。

- テスト・運用を想定した実装上の配慮
  - ルックアヘッドバイアス回避: 多くの処理で datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計。
  - DuckDB 互換性配慮: executemany に空リスト渡さない分岐、list 型バインドの不安定性回避など。
  - ログ出力を細かく実装し、失敗時の挙動を明示（警告・情報ログ）。

### 変更 (Changed)

- 該当なし（初回リリース）

### 修正 (Fixed)

- 該当なし（初回リリース）

### セキュリティ (Security)

- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出して誤動作を防止。
- 環境変数上書きルールに protected セットを導入し、OS 環境変数を .env による上書きから保護。

### 既知の制限 / 注意事項 (Notes)

- OpenAI の呼び出しは外部 API に依存するため、レート制限やネットワーク問題で部分的にスキップすることがあります。モジュール側はフォールバックして処理を継続しますが、結果欠落はあり得ます。
- J-Quants / kabu API などの外部クライアント実装（jquants_client, kabu ステーション周り）は本リリースでの呼び出しポイントを用意していますが、実際の API クライアント実装・認証情報は別途必要です。
- DuckDB に依存する SQL 実行はバージョン差分で挙動が変わる可能性があるため、運用環境での DuckDB バージョン互換性を確認してください。
- 一部の処理（calendar_update_job など）は date.today() を使用しており、バッチ実行時間に依存する挙動がある点に注意してください（ETL の target_date 指定とは区別）。

---

配布後のマイナーバージョンでは、テストカバレッジ強化、OpenAI レスポンスパース耐性向上、各種メトリクス・監視の追加、外部クライアントの抽象化（インターフェース化）などを予定しています。