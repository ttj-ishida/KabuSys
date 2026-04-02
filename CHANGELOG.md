# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

- ルール: https://keepachangelog.com/ja/1.0.0/
- バージョン番号は semver に従います。

## [Unreleased]
（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初期リリース。日本株自動売買プラットフォームのコア機能を実装しました。以下はコードベースから推測した主要な追加点・設計判断・修正点の要約です。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として公開。主要サブパッケージ（data, strategy, execution, monitoring）を __all__ でエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。プロジェクトルート検出（.git / pyproject.toml）に基づき .env と .env.local を読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env のパース処理を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、無効行スキップなど）。
  - 既存 OS 環境変数を保護する protected set を用いた上書き制御（.env.local は override=True）。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DBパス・監視閾値・システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを明示的に取得・検証。

- AI ニュース/NLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出する機能を実装。
  - タイムウィンドウ（JSTベース：前日15:00〜当日08:30）計算ユーティリティ calc_news_window。
  - バッチ処理（1 API 呼び出しあたり最大 _BATCH_SIZE 銘柄）、1銘柄あたりの最大記事数・文字数制限でトークン肥大を抑制。
  - JSON Mode を期待したレスポンス処理と堅牢なバリデーション（results 配列の検査、コード正規化、スコアの数値検査、±クリップ）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。致命的エラー時は当該チャンクをスキップして継続（フェイルセーフ）。
  - DuckDB 互換性を考慮した空パラメータ回避（executemany に空リストを渡さないガード）。

- AI レジーム判定 (kabusys.ai.regime_detector)
  - 日次の市場レジーム判定（'bull' / 'neutral' / 'bear'）を実装。
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して判定。
  - マクロニュース抽出（マクロキーワードセット）→ LLM での macro_sentiment 評価（JSON モード期待）→ スコア合成 → market_regime へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - API 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）、HTTP 5xx はリトライ対象。

- データ（kabusys.data）
  - マーケットカレンダー管理（calendar_management）：market_calendar テーブルを用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants からの差分取得とバックフィル）を実装。DB データがない場合は曜日ベースでフォールバックする設計。
  - ETL パイプライン（pipeline）：差分取得、保存（jquants_client の save_* を利用した冪等保存）、品質チェックの枠組み。ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETLResult は品質問題リスト、エラー一覧、保存件数等を保持し、has_errors / has_quality_errors / to_dict を提供。

- リサーチ（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いたファクター計算（モメンタム、200日MA乖離、ATR、流動性、PER/ROE 等）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターンを一括で取得）、calc_ic（スピアマンランク相関での IC 計算）、rank、factor_summary（count/mean/std/min/max/median）。
  - 外部依存を排し、DuckDB + 標準ライブラリのみで完結する実装方針。

- テストしやすさ / 拡張性
  - OpenAI 呼び出しは _call_openai_api として抽象化しており、ユニットテスト時に差し替え可能（unittest.mock.patch を想定）。

### Changed
- （初期リリースのため該当なし）

### Fixed / Hardened behaviour
- .env 解析ロジックの堅牢化（引用符内でのエスケープ、コメント扱いの改善）。
- OpenAI レスポンスの JSON パース失敗時に、文字列から最外側の {} を抽出して復元するフォールバック処理を追加。
- API エラー処理で status_code の有無に安全に対応（将来の SDK 変更に耐える実装）。
- DuckDB の実装差分（executemany の空リスト不可など）を回避するガードを導入。

### Security
- OS 環境変数の保護機構（protected set）を導入し、.env による意図しない上書きを防止。
- 必須の秘密情報（OpenAI API キー、Slack トークン、J-Quants トークン等）は Settings のプロパティで明示的に取得し、未設定時は ValueError を投げて早期検出。

### Notes / Implementation decisions
- ルックアヘッドバイアス防止のため、いずれの処理も内部で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- AI モジュールは LLM 呼び出しの失敗を也続可能な形で設計（部分失敗を全体停止にしない）。
- market_regime / ai_scores への書き込みは「置換（DELETE → INSERT）」で実装し、部分失敗時に他データを保護。
- J-Quants / kabu API のクライアントは外部モジュール（kabusys.data.jquants_client など）を利用する想定でインターフェースを定義。
- DuckDB を中心に SQL ウォークフローで大量データを処理する前提。互換性のための SQL 記述やウィンドウ関数の使い方に注意。

---

今後のリリースに向けた提案（参考）
- strategy / execution / monitoring サブパッケージの実装状況に応じた取引ルール・実行エンジン・監視アラート機能の明確な変更ログ。
- OpenAI 使用量最適化（プロンプト最適化、キャッシュ、ローカルルールベースのフォールバック）。
- ETL のエラーリトライ／再試行ポリシーや監査ログ出力の強化。
- CI / テストのためのモック用インターフェースとサンプルDBフィクスチャの提供。

---
（注）上記は提示されたコード内容から推測して作成した CHANGELOG です。実際の変更履歴や日付はリポジトリのコミットログに基づいて調整してください。