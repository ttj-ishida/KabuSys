# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは、コードベースから実装内容を推測して作成した変更履歴です。

注意: バージョン番号はパッケージ定義 (kabusys.__version__) に基づきます。

## [Unreleased]

- ドキュメントやテストの追加予定、内部APIの微調整・型注釈強化などを想定。

---

## [0.1.0] - 2026-03-29

初回公開リリース。本リリースでは日本株自動売買プラットフォームの基盤となる以下の主要機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成（__init__.py）を追加。モジュール公開インターフェースを定義。
  - バージョン情報: 0.1.0。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git / pyproject.toml）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` / `.env.local` の読み込み順序と上書きルールを実装（OS 環境変数保護機能を備える）。
  - .env パーサを実装（export プレフィックス対応、単一/二重クォート、エスケープ、インラインコメントの扱いを考慮）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 実行環境判定 (development/paper_trading/live) / ログレベル検証などのプロパティを公開。
  - 必須環境変数未設定時に明示的なエラーを出す `_require` を実装。

- データ層（Data platform）
  - calendar_management: JPX マーケットカレンダー管理、営業日判定ロジック、next/prev/get_trading_days、SQ日判定、夜間バッチ更新ジョブ（J-Quants から差分取得して保存）を実装。
    - DB 登録優先の判定ロジック、未登録時の曜日ベースのフォールバック、最大探索日数で無限ループ防止、バックフィル・健全性チェックを実装。
  - pipeline / etl: ETL パイプラインの基盤を実装（ETLResult データクラスを含む）。
    - 差分取得・バックフィル、品質チェックの取り扱い方針、id_token 注入によるテスト容易性などの設計方針を反映。
  - etl モジュールの公開インターフェースを re-export（ETLResult）。

- 研究（Research）機能
  - research パッケージ初期実装を追加。
  - factor_research: モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）などのファクター計算関数を実装（DuckDB を用いた SQL ベースの実装）。
    - calc_momentum, calc_volatility, calc_value を提供。
    - 200日 MA や ATR 等についてデータ不足時の取り扱い（None / 中立）を考慮。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、rank, factor_summary 等の統計ヘルパーを実装。
    - calc_forward_returns（複数ホライズン対応、入力検証あり）、calc_ic（ランク相関、足りないデータ時は None）、rank（平均ランク処理、同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - zscore_normalize をデータモジュールから利用可能に（research.__init__ 経由で再公開）。

- AI（自然言語処理）機能
  - ai.news_nlp: ニュース記事に対する銘柄単位のセンチメントスコアリング機能を実装。
    - スコアリング対象ウィンドウの計算（前日15:00 JST 〜 当日08:30 JST のUTC変換）および記事集約ロジック。
    - 1銘柄あたりの最大記事数・最大文字数でトリムする対策、バッチ（最大20銘柄）での OpenAI 呼び出し、JSON mode を使った厳密なレスポンス検証。
    - リトライ（429/ネットワーク/タイムアウト/5xx）用の指数バックオフ、レスポンスの厳格バリデーション、スコア ±1.0 でクリップ。
    - 処理後は ai_scores テーブルへ冪等的に保存（該当コードのみ DELETE → INSERT）。
    - フェイルセーフ: API 失敗時は部分スキップし、他の銘柄/チャンクに影響を与えない設計。
  - ai.regime_detector: 市場レジーム判定（'bull' / 'neutral' / 'bear'）機能を実装。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成。
    - ニュース抽出、OpenAI（gpt-4o-mini）呼び出し、再試行ロジック、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - OpenAI 呼び出しはテスト容易性のため専用のラッパー関数に分離しており、ユニットテストでモック可能。

### Changed
- 実装設計上の注意点（全体）
  - すべての時間関係処理は datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB を主要な分析用ローカルDBとして採用し、SQL と Python を組み合わせた処理を行う。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT に相当する保存戦略を前提）。

### Fixed
- 初期リリースのため特記事項なし（実装済みのロジックはエラー処理やログ出力を含め堅牢に設計）。

### Security
- OpenAI API キーや外部サービス認証情報は Settings 経由で環境変数から取得する設計。自動的に .env を読み込むが、環境変数優先・保護（protected keys）を実装して誤上書きを防止。

---

今後の予定（例）
- 単体テスト・統合テストの追加（特に OpenAI 呼び出し部分のモック化テスト）
- ドキュメント（Usage / API reference / Data schema）の整備
- 性能チューニング（DuckDB クエリやバッチサイズ最適化）
- 監視・アラート（Slack 通知等）との連携強化

もし特定の機能や差分の注記（たとえば細かいコミット単位の変更履歴）が必要であれば、その対象ファイルやコミットメッセージ等の情報を提供してください。それらに基づきより詳細なCHANGELOGを作成します。