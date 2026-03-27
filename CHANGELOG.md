# Changelog

すべての注目すべき変更をこのファイルに記録します。  
この変更履歴は「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased: 今後の変更
- 各リリースはバージョンとリリース日を記載し、カテゴリ別に変更点を列挙します。

## [Unreleased]
（無し）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」ライブラリの基盤機能を実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開モジュール一覧を定義。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env および .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val 形式やクォート／コメントを考慮した .env パーサを実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の設定取得を型安全に実装。
    - 必須環境変数未設定時は ValueError を送出。

- AI（NLP）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのニュースセンチメント（ai_score）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・トリミング（記事数・文字数上限）・リトライ（429/ネットワーク/5xx に対する指数バックオフ）・レスポンス検証を実装。
    - DuckDB への冪等書き込み（DELETE → INSERT）による部分失敗耐性。
    - テスト容易性のため OpenAI 呼び出し点に差し替え可能なフックを用意（ユニットテストでの patch を想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存。
    - LLM 呼び出しは gpt-4o-mini を利用。API エラー時はフェイルセーフ（macro_sentiment=0.0）。
    - DuckDB を用いたルックアヘッドバイアス対策（date < target_date 条件など）を徹底。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - マクロキーワード一覧およびシステムプロンプトを定義。

- データ基盤（Data Platform）関連
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブル）: 営業日判定、前後営業日の検索、期間内営業日列挙、SQ（特別清算）日の判定。
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（平日を営業日）を提供。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック（過度に将来の last_date を検出した場合はスキップ）を実装。
    - 最大探索範囲の制限（_MAX_SEARCH_DAYS）やバックフィル（_BACKFILL_DAYS）を導入。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの結果を表す ETLResult データクラスを実装（取得数 / 保存数 / 品質問題 / エラー等を保持）。
    - 差分取得・バックフィル・品質チェックの方針を反映したユーティリティ群を実装。
    - jquants_client と quality モジュールを統合するためのインターフェースを用意。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究用ユーティリティ（Research）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）といった定量ファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、欠損時の扱い（データ不足で None を返す）を明確化。
    - 結果は (date, code) をキーとする dict のリストで返却。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン（複数ホライズン）計算のユーティリティ（calc_forward_returns）。
    - Spearman ランク相関による IC（Information Coefficient）計算（calc_ic）。
    - 値リストをランクに変換するユーティリティ（rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）の計算（factor_summary）。
    - pandas 等に依存せず標準ライブラリと DuckDB のみによる実装。

- 公開 API の整理
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py, src/kabusys/data/__init__.py などで主要関数やユーティリティをエクスポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キー（OPENAI_API_KEY）や各種トークンは環境変数で管理する設計。必須値未設定時は ValueError を送出することで誤設定を早期検出。
- .env 自動読み込みは環境変数優先であり、OS 環境変数は保護される（.env による上書きを防止）。自動ロードを無効化するフラグを提供。

### Notes / Known limitations
- OpenAI に依存する機能（news_nlp, regime_detector）は API レスポンスや利用制限により一部スコアが欠落する場合があるが、フェイルセーフとして欠落時はスコア 0.0 を使用する等の設計を行っている。
- DuckDB の executemany に対する互換性（空リスト不可など）を考慮した実装があるため、古い DuckDB バージョン使用時は一部動作を確認してください。
- モデルは現時点で gpt-4o-mini を想定。将来的なモデル API 変更に備え、API 呼び出し箇所はテストで差し替え可能な構造にしている。
- monitoring モジュールはパッケージ公開リストに含まれているが、本リリースに詳細実装は含まれていません（将来追加予定）。

---

保持方針: 重要な変更のみを記録します。小さな内部変更やリファクタは必要に応じて要約して記載します。