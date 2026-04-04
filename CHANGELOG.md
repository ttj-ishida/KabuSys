# Changelog

すべての注目すべき変更は Keep a Changelog の形式に従って記録します。  
このファイルは安定したリリース履歴のための要約であり、コード（src/ 配下）の実装内容から推測して作成しています。

注: 日付は本ドキュメント作成時点（2026-04-04）を使用しています。必要に応じて調整してください。

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added
- パッケージ初版として kabusys を追加。
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0"、外部公開モジュール群（data, strategy, execution, monitoring）を定義。
- 環境変数 / 設定管理モジュールを追加（kabusys.config）。
  - .env ファイルまたは環境変数からロードする自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に探索して .env / .env.local を読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env の行パーサ (_parse_env_line) は以下に対応:
    - 空行・コメント（#）の無視
    - export KEY=val 形式の処理
    - シングル/ダブルクォート、バックスラッシュエスケープの扱い
    - クォート無しのインラインコメント判定
  - Settings クラスを提供し、J-Quants や kabu API、LINE、DBパスや監視閾値、環境（development/paper_trading/live）、ログレベル等をプロパティで取得・検証。
  - 必須環境変数未設定時は明示的なエラー（ValueError）を発生させるユーティリティ _require を提供。
- AI モジュール（kabusys.ai）を追加。
  - news_nlp.score_news:
    - raw_news と news_symbols からターゲットウィンドウの記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う（calc_news_window）。
    - バッチサイズ、1銘柄あたりの最大記事数・最大文字数制限、JSON mode のレスポンス検証、スコアのクリップなどを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフ再試行を実装。失敗時はフェイルセーフでスキップし続行する設計。
    - DuckDB の executemany の制約に配慮した idempotent な DB 書き込み（DELETE → INSERT）を実装。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70% 重み）とマクロ経済ニュースの LLM センチメント（30% 重み）を合成して、日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う。
    - prices_daily からのクエリは target_date 未満のデータのみを使用する等、ルックアヘッドバイアス対策を徹底。
    - OpenAI 呼び出しに対してリトライ・フェイルセーフ（失敗時 macro_sentiment = 0.0）を実装。
    - OpenAI 呼び出しはモジュール内で独立実装（テスト容易性のため差し替え可能）。
- Data モジュール（kabusys.data）を追加（主要機能の一部を実装）。
  - calendar_management:
    - market_calendar を基にした営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - DB 登録値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得し冪等保存。バックフィル・健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラーなど）を構造化して返却・ログ可能に。
    - pipeline モジュールは差分取得、保存、品質チェックの流れを想定（jquants_client と quality モジュールを組み合わせる設計）。
  - jquants_client との連携を想定した設計（fetch / save 系の呼び出しに対応）。
  - DuckDB を主要なローカル分析 DB として利用する前提。
- Research モジュール（kabusys.research）を追加。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離などのモメンタム指標を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE の算出（PBR/配当利回りは未実装）。
    - 設計として DuckDB の SQL とウィンドウ関数を活用し、外部 API へアクセスしない安全なリサーチ用実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターンを計算。
    - calc_ic: スピアマン（ランク）相関を用いた IC 計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを返すランク関数（丸め処理で ties を安定化）。
  - すべて標準ライブラリ（pandas 等には依存しない）で実装され、研究用途に最適化。
- 共通設計上の注意点・フェイルセーフ実装を多数追加。
  - ルックアヘッドバイアス防止（datetime.today()/date.today() を内部で参照しない設計、ターゲット日ベースの集計）。
  - OpenAI 呼び出しの再試行戦略（指数バックオフ）、JSON レスポンスの堅牢なパースとバリデーション。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）。
  - DuckDB のバージョン差分に配慮したワークアラウンド（executemany の空リスト禁止など）。
  - ロギングを各主要処理に追加し、失敗時は例外を上位へ伝播する前に適切にロールバックや警告ログを出力。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。  
  （ただし各モジュールにおいて API エラー時のフェイルセーフやリトライ実装、ROLLBACK の取り扱い等の堅牢性向上措置を実装）

### Security
- 初回リリースのため該当なし。  
  - 注意点: OpenAI API キーや各種トークンは環境変数経由で取得する設計（Settings を通じて取得）。自動ロードされる .env はプロジェクトルートに基づくため、運用時は .env の取り扱いに注意してください。

---

今後の記載例（参考）
- Unreleased: 進行中の変更（機能追加・リファクタ・バグ修正）を記載。
- バージョンアップ時は [Unreleased] を移動して新しいセクションを追加してください。

もし特定の変更点をより細かく分割（例えば ai/news_nlp の細かな挙動や data/calendar の API 仕様など）して記載したい場合は、どの粒度で出力するか指定してください。