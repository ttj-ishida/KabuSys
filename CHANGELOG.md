# Changelog

すべての変更は Keep a Changelog の形式に従い、重要度に応じて分類しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買プラットフォームのコアライブラリ（データ取得・ETL・研究用ファクター計算・AIニュース解析・市場レジーム判定・カレンダー管理・設定読み込み等）を実装しています。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージバージョンを `0.1.0` として初期実装。
  - top-level のエクスポートを整備（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を探索）によりカレントワーキングディレクトリに依存しない読み込みを実現。
  - 行パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを正しく扱う実装を追加。
  - .env（優先度低）および .env.local（優先的に上書き）を読み込む挙動を提供。OS の既存環境変数を保護するための protected セットを使用。
  - 必須設定取得時に未設定なら ValueError を送出する `_require` と、各種設定プロパティ（J-Quants, kabuAPI, Slack, DB パス, 環境判定・ログレベル判定など）を `Settings` クラスで提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。

- データ / ETL（kabusys.data）
  - ETL パイプライン骨格（`kabusys.data.pipeline.ETLResult` を公開）。
  - ETL の差分更新・バックフィル方針・品質チェック設計を実装（ETLResult に品質問題やエラーの集約）。
  - DuckDB を用いた DB 最大日付取得やテーブル存在確認などのユーティリティ実装。

- カレンダー管理 (`kabusys.data.calendar_management`)
  - JPX マーケットカレンダーの夜間更新ジョブ実装（J-Quants クライアント経由で差分取得、冪等保存）。
  - 営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。DB データ優先、未登録日は曜日ベースでフォールバック。
  - 最長探索範囲の制限や健全性チェック（未来日が異常に遠い場合はスキップ）を導入。

- AI / ニュース解析 (`kabusys.ai`)
  - ニュースNLP スコアリング（`kabusys.ai.news_nlp.score_news`）
    - raw_news と news_symbols を集約して、銘柄ごとに gpt-4o-mini を用いてセンチメントを計算。
    - バッチ処理（1リクエストあたり最大 20 銘柄）、1銘柄あたりの記事数・文字数上限、JSON Mode の応答検証、スコアの ±1.0 クリップを実装。
    - API エラー（429・タイムアウト・ネットワーク・5xx）に対する指数バックオフのリトライ、失敗時はそのチャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code/score のチェック）。
    - 書き込みは部分失敗に備え、既存スコアを不要に消さない（対象コードのみ DELETE → INSERT）方式で実装。
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ冪等書き込み。
    - マクロキーワードで raw_news から記事を抽出して LLM に送信。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
    - OpenAI 呼び出しのリトライ・エラー処理、JSON パース失敗時フォールバックを実装。
    - API キーは引数優先、未設定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を送出。
  - AI モジュールはテスト容易性のため `_call_openai_api` を内部に分離し、単体テストで差し替え可能。

- 研究機能（kabusys.research）
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER・ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高変化率）を DuckDB クエリにより実装。
    - データ不足（例: MA に必要な行数未満）は None を返す挙動。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（複数ホライズン対応）、IC（スピアマンのランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
    - pandas 等外部依存を避け、標準ライブラリ + DuckDB を使用。
  - 研究用ユーティリティの公開（zscore_normalize の再エクスポート等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計判断
- ルックアヘッドバイアス防止のため、いかなる箇所でも datetime.today()/date.today() をスコア計算や DB クエリの直接基準として参照しない設計（target_date を明示的に渡す方式）。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 相当の扱い、部分失敗時に他行を保護）。
- API 呼び出しの失敗はシステム全体停止させない（フォールバック値を用いるか該当チャンクのみスキップ）方針。
- DuckDB バージョン差異（executemany の空リスト不可や配列バインドの不安定性）に配慮した実装。
- OpenAI へのプロンプト・レスポンスは「厳密な JSON」を期待するが、実運用を鑑みて前後余計なテキストが混ざるケースへの復元ロジックを導入。

### Breaking Changes
- 初回リリースのため該当なし。

---

今後の改善候補（今後のリリースで取り組む予定）
- ai スコアリングの更なる堅牢化（モデル切替・ロギング拡張・メトリクス収集）
- ETL の増分実行をより細かく制御する API（並列化・失敗時リトライ戦略）
- テストカバレッジの拡充（DuckDB を用いた統合テストの自動化）
- ドキュメント（API 仕様・データスキーマ）の追加

もし特定ファイルや機能について、より詳細なリリースノートやセクション分け（例: data, ai, research, config ごと）を希望される場合はお知らせください。