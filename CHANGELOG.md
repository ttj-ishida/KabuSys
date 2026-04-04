# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従い、セマンティック バージョニングを採用します。

※ 日付はリリース日です。

## [0.1.0] - 2026-04-04

### Added
- パッケージ初期リリース。主に日本株自動売買プラットフォームのデータ収集・研究・AI解析・運用監視に関するコア機能を実装。
  - パッケージ公開情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に定義。
  - 環境設定 / セッティング（kabusys.config）
    - .env / .env.local の自動読み込み機能（OS 環境変数を保護、.env.local は上書き優先）。
    - .env パーサー実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行コメント取り扱い、インラインコメントの扱い等に対応）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを実装（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別・ログレベル検証 等のプロパティを提供）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）、必須値未設定時に ValueError を送出する _require ユーティリティ。
  - データ関連（kabusys.data）
    - ETL 基盤（kabusys.data.pipeline）
      - ETLResult データクラス（取得件数、保存件数、品質問題、エラー等を集約）。
      - 差分取得・バックフィル・品質チェック設計に対応するためのユーティリティ（最終取得日の判定、テーブル存在チェック等）。
      - DuckDB を前提とした実装。DuckDB の制約（executemany の空パラメータ不可など）を考慮した処理。
    - calendar_management モジュール
      - JPX カレンダー向けの夜間バッチ更新（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存。
      - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
      - DB 登録値優先、登録がない日は土日ベースのフォールバックを行う一貫したロジック。
      - 安全性: 最大探索日数制限、バックフィル・健全性チェックを実装。
    - ETL 用インターフェースの公開（kabusys.data.etl で ETLResult を再エクスポート）。
  - 研究（kabusys.research）
    - factor_research モジュール
      - Momentum: 1M/3M/6M リターン（営業日基準）、200 日移動平均乖離（ma200_dev）を計算する calc_momentum を実装。
      - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility を実装。
      - Value: EPS / PER と ROE を raw_financials（財務）と prices_daily を組み合わせて計算する calc_value を実装。
      - DuckDB 上での SQL ベース実装、欠損・データ不足時の None 扱い。
    - feature_exploration モジュール
      - 将来リターン算出（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）のリターンを LEAD 句で一括取得。
      - 情報係数（IC）計算（calc_ic）：スピアマンのランク相関（ties 平均ランク処理）を実装。データ不足時は None を返す。
      - ランク変換ユーティリティ（rank）：同順位は平均ランク、丸めにより ties 検出漏れを防止。
      - 統計サマリー（factor_summary）：カウント/平均/標準偏差/最小/最大/中央値を算出。
  - AI モジュール（kabusys.ai）
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメントスコアを取得する score_news を実装。
      - チャンク処理（最大 20 銘柄／API コール）、1 銘柄あたり記事数・文字数上限（トークン肥大化対策）を実装。
      - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、既知コードのみ採用、スコア数値チェック、±1.0 でクリップ）。
      - DB 書き込みは部分失敗に強い設計（該当コードのみ DELETE → INSERT）。DuckDB の executemany の制約を考慮。
      - calc_news_window ユーティリティ（JST ウィンドウ → UTC naive datetime）を提供。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
      - マクロセンチメントは news_nlp の窓（calc_news_window）で抽出した記事タイトルを OpenAI へ渡して評価。
      - レスポンスは厳密 JSON を期待。API 失敗時は macro_sentiment = 0.0 でフォールバック（フェイルセーフ）。
      - 冪等 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と、失敗時の ROLLBACK を実装。
  - research パッケージのエクスポート整理（kabusys.research.__init__）で代表的関数を公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

### Notes / 設計上の重要事項
- OpenAI API
  - news_nlp/regime_detector は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須とする。未設定時は ValueError を送出する。
  - LLM 呼び出しは gpt-4o-mini + JSON mode を想定。レスポンスパースエラーや API 障害はフェイルセーフで処理を継続（多くの場合スコアを 0 にフォールバック）。
- 時間に関するバイアス対策
  - すべての解析関数は datetime.today()/date.today() による暗黙参照を避け、明示的な target_date 引数で処理を行う（ルックアヘッドバイアスの防止）。
- DB 前提・互換性
  - 実行は DuckDB を前提。実装はいくつかの DuckDB バージョン互換性制約（例: executemany に空リストを与えない）を考慮している。
- トランザクション安全性
  - 重要な DB 更新は明示的な BEGIN / COMMIT / ROLLBACK を使用。ROLLBACK が失敗した場合は警告ログを記録して例外を再送出する。

### Known limitations / TODO
- strategy / execution / monitoring パッケージの詳細（このリリースでの公開はモジュール名のみ。実装内容は別途拡充予定）。
- 一部の細かいファクター（PBR、配当利回り等）は未実装（calc_value 内に記載）。
- OpenAI レスポンスの仕様変更や SDK 変更による挙動影響を受ける可能性があるため、将来的に依存部分の抽象化を検討。

---

今後のリリースでは、実運用向けの注文実装（execution）、監視・運用自動化（monitoring）、戦略実装（strategy）の充実、そして品質チェックの強化を予定しています。