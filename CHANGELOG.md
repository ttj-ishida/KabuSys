# Changelog

全ての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）準拠です。内容は提供されたコードベースから推測して記載しています。

## [Unreleased]

- 今後の変更点はここに記載します。

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システムのコアライブラリを実装しています。主な機能・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - export KEY=val 形式やクォート、インラインコメントなどを考慮した .env パーサーを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用）。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants / kabu API / LINE / DB / 監視 / システム設定）。
  - 環境変数の必須チェック _require を実装（未設定時は ValueError）。

- AI 関連 (src/kabusys/ai)
  - ニュース NLP スコアリング: news_nlp.score_news
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini・JSON Mode）へバッチ送信して銘柄ごとに -1.0〜1.0 のスコアを算出。
    - バッチサイズ、記事数・文字数制限、リトライ（429/ネットワーク/タイムアウト/5xx）や指数バックオフを実装。
    - レスポンス検証とスコアクリップ（±1.0）、部分成功時は既存データを保護する idempotent な DB 書き換え（DELETE→INSERT）。
    - calc_news_window（JST の前日15:00〜当日08:30 相当の UTC 範囲）を実装。
  - 市場レジーム判定: regime_detector.score_regime
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しのリトライとフェイルセーフ（API 失敗時に macro_sentiment=0.0）。
    - Look-ahead バイアス防止のため datetime.today()/date.today() を直接参照しない設計。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理: calendar_management
    - market_calendar テーブルに基づく営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にデータが無い場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック付き）。
  - ETL パイプライン: pipeline
    - 差分取得→保存→品質チェックの流れを想定した ETLResult データクラスを実装。
    - ETLResult は取得/保存件数、品質問題、エラー概要を保持し、to_dict でシリアライズ可能。
  - ETL インターフェースを etl モジュールで公開（pipeline.ETLResult を再エクスポート）。

- リサーチ / ファクター (src/kabusys/research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）などファクター計算関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用した高効率実装。データ不足時は None を返す挙動。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。
  - research パッケージの __all__ に主要関数を公開。

### 変更 (Changed)
- 初期設計上の安全性と互換性を重視
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮して条件分岐を追加。
  - OpenAI レスポンスの JSON パースにおいて余計な前後テキスト混入ケースを想定して {} を抽出する復元処理を実装。
  - API エラー処理で status_code が存在しない場合でも安全に扱うため getattr を使用。

### 修正 (Fixed)
- この初期バージョンはコード構成・機能実装に焦点を当てており、既知のバグ修正は該当なし（将来追加予定）。

### セキュリティ / 注意点 (Security / Notes)
- OpenAI 利用:
  - news_nlp と regime_detector は OpenAI API（gpt-4o-mini、JSON Mode）に依存します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
  - API 呼び出しはネットワーク依存のため、呼び出し失敗時はフェイルセーフ（スコアを 0 にする等）で継続する設計です。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings のプロパティ参照で未設定時は例外を送出）。
  - KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。
  - 自動 .env ロードはプロジェクトルート判定に依存（.git または pyproject.toml）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DB パス:
  - デフォルトで duckdb は data/kabusys.duckdb、監視用 sqlite は data/monitoring.db を使用（環境変数で上書き可能）。

### 既知の制限 (Known limitations)
- 現時点での AI スコアは LLM 出力の妥当性に依存するため、実運用前に必ず評価・監査してください。
- 一部の SQL バインディングや DuckDB バージョン差異により挙動が変わる可能性があるため、使用する DuckDB バージョンでの動作確認が必要です。
- 本バージョンでは発注（execution）や戦略（strategy）の実装は公開API に向けた構成のみで、実際の発注ロジックや外部接続の動作検証は別途必要です。

## 謝辞
- この CHANGELOG は提供されたコードから機能・設計を推測して記載しています。実際のリリース履歴やドキュメントと差異がある場合は本ファイルを正式な変更履歴に合わせて更新してください。