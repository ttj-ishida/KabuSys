# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。  
初期リリース（0.1.0）の内容はソースコードから推測して記載しています。

全般的な注意
- 日付は本ファイル作成日（2026-04-04）を使用しています。
- 実装の要点・設計方針・フェイルセーフ挙動等も合わせて記載しています。

## [0.1.0] - 2026-04-04

### Added
- パッケージの初期リリースを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にてバージョンと公開モジュールを定義。

- 環境設定管理（kabusys.config）
  - Settings クラスを提供し、アプリケーション設定を環境変数から取得する公開 API を実装。
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - 読み込みの優先度: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途想定）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 必須変数取得時に未設定なら例外を投げる _require 実装。
  - 各種設定項目をプロパティで提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム環境判定など）。
  - KABUSYS_ENV と LOG_LEVEL の値検証ロジックを実装（不正値時は ValueError）。

- AI 関連（kabusys.ai）
  - ニュース向け NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None) を実装し、raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ上書き保存する処理を実現。
    - 時間ウィンドウ（前日15:00 JST〜当日08:30 JST）計算の calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数制限（トークン肥大化対策）を実装。
    - OpenAI 呼び出しは JSON Mode を用い、レスポンスバリデーション（results リスト・code/score 検証・数値クリップ）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。その他エラーはスキップのフェイルセーフ挙動。
    - テスト容易性のため OpenAI 呼び出し箇所を置き換え可能（_call_openai_api を patch 可能）。
    - スコアは ±1.0 にクリップし、取得成功した銘柄のみを DELETE → INSERT にて置換することで部分失敗時の保護を実現。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None) を実装。ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次のレジーム（bull/neutral/bear）を計算し、market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込む。
    - マクロニュース抽出ロジック（マクロキーワードによるタイトル検索）、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - LLM のレスポンスは厳密な JSON 期待（{"macro_sentiment": 0.0}）で処理。リトライポリシー・5xx 判定等を実装。
    - look-ahead バイアスを避ける設計（date 未満のデータのみ利用、datetime.today() を参照しない）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理 API の夜間バッチ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（冪等）を行う。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に登録がない場合は曜日ベース（平日）でフォールバックする設計。最大探索日数制限や健全性チェック（将来日付の異常検知）を実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装し、ETL の取得数・保存数・品質問題・エラー一覧等を集約可能に。
    - pipeline モジュールの要件に沿った差分更新、バックフィル、品質チェックの設計方針を実装（コード内ドキュメント）。
    - etl モジュールで ETLResult を公開エクスポート（再エクスポート）するインターフェースを追加。
  - 共通ユーティリティ：テーブル存在確認や最大日付取得などの DB ヘルパーを実装。

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュールを実装し、以下のファクター計算関数を追加:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value(conn, target_date): PER（EPS 判定）、ROE（raw_financials から最新レコード）を計算。
  - feature_exploration モジュールを実装し、以下を追加:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターン（LEAD を使用した一括取得）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク）による IC 計算（ties を平均ランクで扱う）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
    - rank(values): 同順位を平均ランクで処理するランク化ユーティリティ。
  - research パッケージの __all__ を整備して主要関数を公開。

### Changed
- （初期リリースのため特になし）

### Fixed
- （初期リリースのため特になし）

### Notes / 設計上の重要点
- 外部 API 呼び出し（OpenAI / J-Quants）はリトライとフォールバック（スコア0.0、スキップ等）を基本とし、処理の中断を避けるフェイルセーフ設計。
- ルックアヘッドバイアス防止のため、日付取り扱いで datetime.today()/date.today() を直接参照しない設計（関数引数で target_date を注入）。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定の save_*）、部分失敗時に既存データを無闇に消さない工夫あり。
- DuckDB を主要なデータストアとして想定。DuckDB の executemany の挙動（空リストの制約）を考慮した実装になっている。
- テスト容易性のため、OpenAI 呼び出しポイントの差し替え（patch）を意図した実装がされている。
- 外部依存は最小限（標準ライブラリ + duckdb + openai 等）に抑え、pandas 等に依存しない実装を採用している箇所がある。

---

今後のリリースでは以下が想定されます（アイデア）:
- ai モジュールの追加評価指標（信頼区間・応答検証の強化）
- ETL の CLI / スケジューリング統合
- モニタリング・実行（execution, monitoring）モジュールの具体的な実装と文書化
- 単体テスト / 結合テストの追加と CI 設定

もし CHANGELOG に追加したい項目や日付・表現の修正があれば指示してください。