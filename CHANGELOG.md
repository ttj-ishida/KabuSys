CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
日付はリリース日を示します。

[Unreleased]
-------------

- なし（初回リリースのため未リリース項目はありません）。

[0.1.0] - 2026-04-04
-------------------

Added
- 初版リリース（kabusys 0.1.0）。
  - パッケージの公開エントリポイントを追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 環境変数・設定管理（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env ファイルパーサ実装（export 形式・シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
  - 環境変数取得ユーティリティ（Settings クラス）を提供。
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY（参照）等の主要設定をプロパティとして公開。
    - デフォルト値（KABUSYS_ENV=development, LOG_LEVEL=INFO, 各種 DB パスや監視閾値）を用意。
    - env/log_level のバリデーション（許可値以外は ValueError）。
- ニュースNLP（src/kabusys/ai/news_nlp.py）。
  - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して ai_scores テーブルへ保存。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・記事数/文字数トリムを実装（トークン肥大化対策）。
  - 再試行（429/ネットワーク/タイムアウト/5xx）用の指数バックオフを実装。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト・code/score チェック、スコアのクリップ）を行い、失敗時は個別にスキップして継続する設計。
  - テスト用に _call_openai_api を patch 可能（unittest.mock で差し替え）。
- 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で書き込み。
  - マクロキーワードによる記事フィルタリング、OpenAI 呼び出し、再試行、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - DB 書き込みは冪等に行う（BEGIN / DELETE / INSERT / COMMIT、例外時に ROLLBACK 試行）。
- データプラットフォーム（src/kabusys/data 以下）。
  - ETL パイプライン／ユーティリティ（pipeline.py, etl.py）の初期実装。
    - ETLResult データクラス（取得数・保存数・品質問題・エラー等を保持）。
    - 差分取得・backfill・品質チェックを想定した設計。
  - カレンダー管理（calendar_management.py）。
    - market_calendar テーブルを参照する営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants API からの夜間更新ジョブ calendar_update_job（バックフィル・健全性チェック・差分取得・保存）。
    - DB 未取得時の曜日ベースフォールバック実装（土日を非営業日扱い）。
- 研究（research）モジュール（src/kabusys/research）。
  - ファクター計算（factor_research.py）：モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR）、流動性指標、バリュー（PER, ROE）計算。
  - 特徴量探索（feature_exploration.py）：将来リターン計算、IC（Spearman）計算、rank/summary ユーティリティ。
  - zscore_normalize は kabusys.data.stats からの再エクスポートを想定。
- テスト性・運用性向上のための設計上の配慮。
  - API 呼び出し箇所は差し替え可能にしてユニットテストを容易化。
  - ルックアヘッドバイアス防止の方針をコードレベルで徹底（date.today()/datetime.today() を直接参照しない設計、クエリに date < target_date などの排他条件）。
  - DuckDB の executemany の制約（空リスト不可）への対応。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 外部 API（OpenAI / J-Quants / kabuステーション）用のキーは環境変数で管理するよう明示。
  - 必須環境変数が未設定の場合は明確な ValueError を発生させる（例: OPENAI_API_KEY 未設定時に score_news/score_regime がエラー）。
- .env 自動ロード時の既存 OS 環境変数保護機能（protected set を利用して上書きを制御）。

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を想定し、JSON mode を利用する設計。API レスポンスのフォーマットに冗長な前後テキストが混ざる場合でも復元できるように最外の {} を抽出する耐性を実装。
- ai スコアは ±1.0 にクリップ。regime スコアも -1.0〜1.0 にクリップしてカテゴリ付け（bull / neutral / bear）。
- DB 書き込みは可能な限り冪等性を保つ（既存行の DELETE → INSERT、部分失敗時に他コードの既存データを保護する戦略）。
- 日付・時間は基本的に date / naive datetime（UTC）で扱う。ニュースウィンドウは JST 基準で計算してから UTC naive datetime に変換して DB 比較に使う。
- DuckDB を主要なローカル分析 DB として利用する前提（デフォルトパス: data/kabusys.duckdb、監視用 sqlite: data/monitoring.db）。
- 既知の制約:
  - news_nlp / regime_detector は外部 API の利用・回線状況に依存するため、API 失敗時は該当処理をスキップしてフェイルセーフ（0.0 相当の中立値）を使う設計。完全性を保証するものではない。
  - timezone を含む datetime 混用は避ける意図だが、外部 DB/データソースの timezone 整合は利用者側で注意が必要。

Deprecated
- なし

Removed
- なし

Contributors
- 初版コードベース（機能分割とモジュール実装に関わる設計・実装を含む）。

今後の予定（計画）
- strategy / execution / monitoring モジュールの実装拡張（エントリポイントに含まれているが今回の初版では未実装または別ファイルに分割済みの可能性あり）。
- 追加の品質チェックルール、CI/テストカバレッジ強化、実運用向けの監視・アラート機能の拡張。

お問い合わせ
- 実装上の疑問やバグ報告、改善提案があればリポジトリの Issue をご利用ください。