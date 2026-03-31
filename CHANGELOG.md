# Changelog

すべての注目すべき変更を Keep a Changelog の形式に従って記載します。バージョンとカテゴリはコードベースの実装・コメントから推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 設定・環境変数管理の自動読み込みに対する改善計画
  - .env のパースや優先度ロジック（.env -> .env.local -> OS環境変数）についての追加ユニットテストやドキュメント充実を予定。
- ai モジュールの拡張案
  - News/Regime モジュールでの OpenAI モデル選択や JSON モードの堅牢化、レスポンス検証の強化、複数モデル対応の検討。
- データ品質チェックの強化
  - ETL の quality チェック結果に基づく自動通知/アクションフローの追加計画。

### Changed
- 将来のリリースで DuckDB の互換性や executemany の空リスト制約に関する改善を予定。
- ニュース分析のトリム・バッチ戦略や retry/backoff ポリシーのパラメータ調整を検討。

### Fixed
- （予定）OpenAI API エラー時の挙動やログ出力の調整、より詳細なメトリクス収集を行う予定。

---

## [0.1.0] - 2026-03-31

初回公開（推測）。以下はこのコードベースで実装されている主要機能と設計上の注意点をまとめたものです。

### Added
- 基本パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local ファイルの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env パースの堅牢化:
    - コメント行・空行・export プレフィックス対応。
    - シングル/ダブルクォートのエスケープ対応。
    - インラインコメントの除去（クォートあり/なしで取り扱いを分岐）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - 環境変数保護ロジック（OS環境変数を protected として上書きを制御）。
  - Settings クラスで構成値をプロパティ提供（J-Quants・kabu API・Slack・DB パス・環境名・ログレベル等）。
  - env/log_level 値のバリデーション（許容値セットを用意）。
  - 必須環境変数未設定時は ValueError を送出する _require 実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
  - 設計上の注力点:
    - 前日15:00 JST〜当日08:30 JST のニュース窓を calc_news_window で明示的に計算（UTC naive datetime で扱う）。
    - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトリム。
    - 最大 _BATCH_SIZE（20銘柄）単位のバッチ処理。
    - API 呼び出しは JSON mode を利用、出力厳格な JSON を期待。
    - リトライポリシー: 429/ネットワーク/タイムアウト/5xx に対するエクスポネンシャルバックオフ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト確認、code 正規化、数値チェック、±1.0 クリップ）。
    - DuckDB への書き込みは部分失敗に配慮して「対象コードのみ DELETE → INSERT」する冪等処理。
    - テスト容易性のため _call_openai_api を patch できる構造。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（70% 重み）とマクロニュース由来の LLM センチメント（30% 重み）を合成して 'bull'/'neutral'/'bear' を算出。
  - マクロニュース抽出は feature: マクロキーワードリストでフィルタ（最大 20 件）。
  - LLM 呼び出しは独立実装でテスト差し替え可能。
  - API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
  - レジーム結果は market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
  - ルックアヘッドバイアス回避のため、target_date 未満のみを利用する設計。

- リサーチ / ファクター計算（kabusys.research）
  - calc_momentum: 1M/3M/6M リターン、ma200 乖離計算（データ不足時は None）。
  - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率等を算出。
  - calc_value: raw_financials から最新財務データを取得し PER・ROE を計算（EPS 0 や欠損時は None）。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得可能。
  - calc_ic / rank / factor_summary: ランク相関（Spearman）計算、ランク化ユーティリティ、基本統計量サマリーを実装。
  - 全関数は DuckDB の prices_daily / raw_financials を参照し、外部トレード実行等へはアクセスしない安全設計。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - カレンダー夜間バッチ（calendar_update_job）で J-Quants から差分取得し冪等保存、バックフィルや健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得件数・保存件数・品質問題・エラー等を格納）。
    - 差分更新、バックフィル、品質チェックの実装方針を含む ETL 基盤の基礎実装。
  - 各種内部ユーティリティ（テーブル存在チェック、最大日付取得、date 型変換など）を実装。

### Changed
- パフォーマンス / 安定化上の工夫を多数実装
  - DuckDB の SQL ウィンドウ関数や ROWS BETWEEN を活用して移動平均・ATR 等を効率的に算出。
  - executemany の空リスト制約回避（DuckDB 0.10 を想定した分岐）。
  - OpenAI 呼び出しに timeout/pagination 等の考慮（timeout=30 を設定）。

### Fixed
- エラー・例外ハンドリングの強化
  - OpenAI API の様々な例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対して明確なリトライ/フォールバック戦略を実装。
  - DB 書き込み失敗時は ROLLBACK を試み、ROLLBACK 失敗は警告ログで通知。
  - JSON パース失敗や不正レスポンスを安全に無視（スコア=0 またはスキップ）することで ETL/スコア生成の継続性を確保。

### Removed
- （該当なし）初期リリースのため削除履歴は無し。

### Security
- OpenAI API キーやその他必須トークンを Settings 経由で取り扱い、未設定時は明示的エラーを出す設計により誤設定を早期に検出。

---

注記（実装上の重要ポイント）
- ルックアヘッドバイアス回避: ニュース/レジーム/ETL/リサーチのいずれのモジュールも内部で date.today() を直接参照せず、関数呼び出し側が target_date を渡す設計になっている点が特徴。
- テスト性: OpenAI への実際の呼び出しを差し替え可能（_call_openai_api を patch）にするなどテストしやすい構造を意識している。
- DuckDB 互換性: executemany の空リスト制約など実装に DuckDB のバージョン差分を意識したワークアラウンドが含まれる。
- 未実装の拡張点（コード内コメントより）: PBR・配当利回り等のバリュー指標は未実装。将来的に補完予定。

もしリリースノートをさらに細分化（モジュールごとの変更点をリスト化）したり、各関数・API の利用例・既知の制約 (Known issues) を追記したい場合は、対象範囲を指定してください。