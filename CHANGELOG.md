# Changelog

すべての変更は Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-01

初回公開リリース。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。公開モジュール群を __all__ で定義。
  - バージョン情報を追加: 0.1.0。

- 環境設定 / ロード
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索する実装を追加（パッケージ配布後でも安定して動作）。
    - .env ファイルパーサを実装:
      - export KEY=val 形式対応、シングル/ダブルクォートとエスケープ処理対応。
      - 行末コメントの扱い（クォートなしで # の直前がスペース/タブならコメントと扱う）を実装。
    - 自動ロード順序: OS環境変数 > .env（読み込み、未設定のみセット） > .env.local（上書き可）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須キー取得ヘルパー _require と Settings クラスを実装（J-Quants / kabu / Slack / DB / 監視設定 / システム設定）。
    - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）と便利プロパティ（is_live / is_paper / is_dev）。

- AI ニュース解析
  - ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）。
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄／コール）、記事数・文字数上限でトリム制御（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（API失敗時はスキップして継続）。
    - レスポンス検証: JSON 抽出、"results" 構造の検査、未知コードの無視、スコアの数値検証、±1.0 でクリップ。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時に既存データを保護。
    - ニュース取得ウィンドウ計算ユーティリティ calc_news_window（JST ベース／UTC 変換）を実装。

  - 市場レジーム判定モジュールを追加（kabusys.ai.regime_detector）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルに書き込む処理を実装。
    - マクロ記事抽出はキーワードフィルタ（_MACRO_KEYWORDS）を使用。記事なしの場合は LLM 呼び出しをスキップして macro_sentiment=0.0 とする。
    - OpenAI 呼び出しは JSON Mode（gpt-4o-mini）を利用し、リトライ／バックオフ／500系と非500系の扱いを区別。失敗時は警告ログを出してフォールバック。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試み上位に再送出。

- データプラットフォーム
  - データ／カレンダー管理モジュールを追加（kabusys.data.calendar_management）。
    - market_calendar を元にした営業日判定 API を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動を提供。
    - カレンダー夜間更新ジョブ calendar_update_job を実装。J-Quants クライアントから差分取得し冪等保存、バックフィルと健全性チェックを実装。
    - 最大探索日数の保護（_MAX_SEARCH_DAYS 等）や future-date の健全性チェックを導入。

  - ETL パイプライン（kabusys.data.pipeline）を追加。
    - 差分更新・保存（jquants_client の save_* を利用して冪等に保存）・品質チェック統合のための骨組みを実装。
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL 実行結果（取得数、保存数、品質問題、エラー）を表現し、辞書化ユーティリティを提供。
    - テーブル存在チェックや最大日付取得などのユーティリティ関数を実装（DuckDB 前提）。

- リサーチ / ファクター計算
  - 研究用モジュール群を追加（kabusys.research）。
    - factor_research: calc_momentum, calc_volatility, calc_value を実装。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None として扱う）。
      - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
      - Value: raw_financials を参照して PER（EPS が 0/欠損なら None）、ROE を計算。
      - すべて DuckDB クエリベースで実装し、外部 API へはアクセスしない設計。
    - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ρ による IC 計算）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
      - calc_forward_returns は複数ホライズンをまとめて効率的に取得するクエリを構築。
      - calc_ic は None / 非有限値を除外し、有効レコードが 3 未満なら None を返す。
    - zscore_normalize は kabusys.data.stats から再エクスポート（__init__ にて公開）。

- 一般的な堅牢性設計
  - ルックアヘッドバイアス回避: datetime.today()/date.today() の直接参照を避け、関数に target_date を明示的に渡す設計。
  - OpenAI 呼び出しについてはモジュール内で専用のラッパー関数を用意し、テスト時に差し替え可能（unittest.mock.patch を想定）。
  - DuckDB に対する executemany の空リスト制約など、実行環境差に配慮した実装上の注意点を反映。
  - ロギング（情報、警告、例外）を適所に追加。

### Changed
- （初回公開のため該当なし）

### Fixed
- （初回公開のため該当なし）

### Deprecated
- （初回公開のため該当なし）

### Removed
- （初回公開のため該当なし）

### Security
- 機密情報（OpenAI / J-Quants / Kabu API / Slack トークン等）は環境変数経由で取得する設計。設定の読み込み・上書きの制御（protected set）を導入し、OS 環境変数の保護に配慮。

---

## 注意事項 / 既知の制約
- OpenAI API キー（OPENAI_API_KEY）、J-Quants / kabu / Slack 関連の環境変数は本パッケージ外で適切に設定する必要があります。未設定時は一部関数が ValueError を送出します。
- OpenAI 呼び出しは実運用では API コスト・レイテンシを伴います。API の利用方法（モデル選定・バッチサイズ等）は初期設計値を設定していますが、運用状況に応じた調整を推奨します。
- DuckDB のバージョン差異（executemany の空リスト挙動など）に注意してください。
- 本リリースは機能実装フェーズの初版です。より詳細なテスト、ドキュメント、運用監視、例外処理の拡張は今後のイテレーションで追加予定です。

もし CHANGELOG に追記してほしい差分や、特定モジュールごとの詳細（関数一覧、引数仕様、例）を出力してほしい場合は教えてください。