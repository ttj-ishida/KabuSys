# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

現在のバージョン方針: セマンティックバージョニングに従います。

## [Unreleased]
- なし

---

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買およびリサーチ用の基盤ライブラリを追加しました。主な機能と設計方針は以下の通りです。

### Added
- パッケージの基本情報
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 高度な .env パーサ実装：
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォート有無で挙動を区別）。
  - .env の上書き制御（override と protected set を利用して OS 環境変数を保護）。
  - Settings クラスでアプリ設定をラップ（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境・ログレベル検証等）。
  - 環境値のバリデーションと必須項目チェック（未設定時は ValueError）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
  - ニュースウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 相当の UTC 範囲）。
  - 1チャンク最大 20 銘柄、1銘柄あたり最大記事数/最大文字数でトリムしてトークン肥大を抑制。
  - JSON Mode を用いた API 呼び出しとレスポンスバリデーション（results 配列、code/score 検証、数値変換、スコアクリップ ±1.0）。
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。非再試行のエラーはスキップして継続（フェイルセーフ）。
  - DuckDB への書き込みは冪等性を考慮（取得成功した code に対して DELETE → INSERT を実行）。DuckDB executemany の空リスト問題に配慮。
  - テスト容易性: OpenAI 呼び出し箇所は差し替え可能（ユニットテストのための patch ポイントを確保）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
  - マクロキーワードによる raw_news フィルタリング、最大記事数制限、OpenAI 呼び出しによるマクロセンチメント取得。
  - LLM 呼び出し失敗時は安全に macro_sentiment=0.0 として継続。リトライ/バックオフと 5xx 判定ロジックを実装。
  - レジームスコア合成と閾値判定、market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。

- データ/ETL 基盤（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラーリストを保持）。
  - 差分更新・バックフィル・品質チェックを想定した ETL 設計（J-Quants API を利用する想定）。
  - ETL の設計方針として「部分失敗を許容して他データを保護する」「id_token 注入でテスト容易性確保」などをドキュメント化。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由でデータ取得 → 保存（オンコンフリクト）するフロー。
  - 営業日判定ユーティリティ群を実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB にカレンダーがない／一部しかない場合は曜日ベースでフォールバック（週末は非営業日）。
  - next/prev/get_trading_days で DB 値を優先し、未登録日は一貫して曜日フォールバックを採用。
  - 健全性チェック（未来日に対する逸脱防止）、バックフィル日数、探索上限日数を導入。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - calc_value: PER, ROE（raw_financials から最新レコードを参照）。
  - 特徴量探索（feature_exploration）を実装:
    - calc_forward_returns: 任意ホライズンの将来リターンを取得（horizons バリデーションあり）。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効レコードが 3 件未満なら None）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる ties 対応）。
  - 設計方針:
    - DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照（本番の発注 API 等にはアクセスしない）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。

- データユーティリティ
  - calendar, pipeline, etl などが jquants_client を通じて外部 API と連携する想定で実装。
  - DuckDB ベースのクエリ中心実装によりパフォーマンスと互換性を考慮。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

Notes / 設計上の重要ポイント（ドキュメント要約）
- ルックアヘッドバイアス対策: 日付計算や DB クエリでは target_date 未満/以前のデータのみを使用し、datetime.today()/date.today() に依存しない。
- フェイルセーフ: OpenAI 等の外部 API 失敗時はスコアを 0.0 にフォールバックするか該当チャンクをスキップし、処理全体の継続性を優先。
- 冪等性: DB 書き込みは DELETE → INSERT 等で既存データの上書きを行い、部分失敗時に他データを消さない工夫を施している。
- テスト容易性: OpenAI 呼び出し等は内部関数を差し替え可能にし、ユニットテストでモックしやすい構造にしている。

（将来的なリリースでは、strategy / execution / monitoring モジュールの詳細な実装、テストカバレッジ・CI 設定、ドキュメントの充実化、互換性ポリシー等を追加予定です。）