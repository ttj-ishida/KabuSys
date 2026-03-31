# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」準拠です。

※ この CHANGELOG は渡されたコードベースの内容から推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース想定 — 日本株自動売買/データプラットフォーム基盤の実装を追加。

### Added
- パッケージのエントリポイント
  - パッケージメタ情報を含む `src/kabusys/__init__.py` を追加（__version__ = "0.1.0"）。
- 環境設定管理
  - `src/kabusys/config.py`
    - .env ファイルおよび環境変数の自動ロード機能（プロジェクトルートを .git / pyproject.toml で探索）。
    - `.env` の行パーサ（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理に対応）。
    - `.env.local` を上書きとして読み込むロジック。OS 環境変数を保護する protected 機構。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラス（J-Quants / kabu / Slack / DB パス / 監視設定 / 環境判定 / ログレベル検証などのプロパティ）。
- AI（LLM）機能
  - `src/kabusys/ai/news_nlp.py`
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを取得して `ai_scores` テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大 20 銘柄／チャンク）、記事数/文字数トリム、レスポンスバリデーション（JSON 抽出、results フォーマット、コードの正規化、数値検証、スコアクリップ ±1）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。API 呼び出しはテスト時に差し替えやすい実装。
    - フェイルセーフ設計：API 失敗時はスキップ継続（例外を上位に投げず影響を局所化）。
  - `src/kabusys/ai/regime_detector.py`
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは `news_nlp.calc_news_window` を使用して期間を決定、OpenAI を呼び出して JSON レスポンスからスコア抽出。
    - リトライ・フェイルセーフ処理、DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - look-ahead バイアスを避ける設計（target_date 未満のデータのみ参照する）。
- データプラットフォーム機能
  - `src/kabusys/data/calendar_management.py`
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - 夜間バッチ更新ジョブ（calendar_update_job）：J-Quants から差分取得し idempotent に保存、バックフィル、健全性チェックあり。
    - DB 未登録日は曜日ベースでフォールバックする一貫した挙動。
  - `src/kabusys/data/pipeline.py` & `src/kabusys/data/etl.py`
    - ETL の結果を表す `ETLResult` データクラスを定義（取得数 / 保存数 / 品質問題 / エラーの集約、辞書化ユーティリティ）。
    - ETL パイプライン設計方針（差分取得、backfill、品質チェックの振る舞い、id_token 注入でテスト容易化）を実装に反映。
    - `etl.py` で pipeline.ETLResult を再エクスポート。
  - J-Quants クライアント連携のプレースホルダ（`kabusys.data.jquants_client` を参照する実装）。
- 研究（Research）機能
  - `src/kabusys/research/*`
    - `factor_research.py`: モメンタム（1M/3M/6M）、MA200乖離、ATR（20日）、平均売買代金・出来高比率、財務指標（PER/ROE）等のファクター計算（DuckDB を用いた SQL ベース実装）。
    - `feature_exploration.py`: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
    - `__init__.py` で主要関数をエクスポート。データ系ユーティリティ（zscore_normalize）は `kabusys.data.stats` から再利用。
- モジュール分割・テスト性
  - OpenAI 呼び出しを内部的にラップしており、ユニットテストでの patch による差し替えを想定した設計。
  - LLM レスポンスの頑健なパース・バリデーション実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- pipeline._get_max_date に実装途中と思われる箇所があります（ファイル末尾付近で `return date.fro` のようなタイプミス／未完了の痕跡が見られます）。本番利用前に修正が必要です。
- `src/kabusys/data/__init__.py` が空であり、モジュールの公開 API やエクスポートの整理が未完の可能性があります。
- 一部の外部依存（OpenAI SDK、jquants_client、DuckDB テーブルスキーマ等）に依存するため、実行には環境整備が必要です。
- AI（LLM）機能は外部 API 利用のためコスト・レート制限の考慮が必要。リトライ・バックオフは実装済みだが、運用ポリシーの検討を推奨します。

### Security
- 環境変数読み込み時に OS 環境変数を保護する機構（protected set）が実装されています。機密情報の取り扱いには注意してください。

---

（この CHANGELOG はコードから推測して作成しています。実際の変更履歴やバージョン運用方針に合わせて適宜編集してください。）