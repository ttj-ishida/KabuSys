# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成した初期リリースの要約です。

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

### 追加 (Added)
- パッケージ基礎
  - `kabusys` パッケージを追加。パッケージバージョンは 0.1.0。
  - パッケージ公開インターフェースに data / strategy / execution / monitoring を含める（__all__）。

- 設定・環境変数管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動ロード機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
  - `.env` のパース処理を強化：export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどに対応。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 必須環境変数取得ヘルパー `_require` と各種設定プロパティを持つ `Settings` クラスを追加。
  - 環境値の検証ロジックを実装（KABUSYS_ENV の許容値、LOG_LEVEL の許容値など）。
  - データベースパス、監視用PID/フラグパス、リソース閾値（CPU/メモリ/ディスク）などのデフォルト設定を提供。

- AI モジュール（OpenAI を利用したニュース解析）
  - `kabusys.ai.news_nlp`
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して `ai_scores` テーブルへ保存する処理を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する `calc_news_window` を実装。
    - バッチ送信（最大 20 銘柄/チャンク）、記事数/文字数トリム（最大記事数・最大文字数）などトークン肥大化対策を実装。
    - API リトライ（429／ネットワーク断／タイムアウト／5xx）を指数バックオフで実装。レスポンス検証ロジック（JSON 抽出、results の形式検査、スコアの数値化・クリップ）を追加。
    - 部分失敗に配慮した冪等書き込み（DELETE → INSERT）を実装し、DuckDB の互換性（executemany の空リスト扱い）に配慮。
    - テスト用に `_call_openai_api` を差し替え可能に設計。

  - `kabusys.ai.regime_detector`
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する処理を実装。
    - prices_daily から MA200 比を計算する `_calc_ma200_ratio`、マクロ記事抽出 `_fetch_macro_news`、LLM コール `_score_macro` を実装。
    - API キー解決、失敗時のフェイルセーフ（macro_sentiment=0.0）やリトライ処理、最終的なスコア合成と `market_regime` への冪等書き込みを実装。
    - 設計上ルックアヘッドバイアスを防ぐ（内部で datetime.today() を参照しない、DB クエリの排他条件など）。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー（market_calendar）を元に営業日判定、翌営業日/前営業日取得、期間内営業日リスト取得、SQ日判定などのユーティリティを実装。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日）を使用する整合的なロジックを提供。
    - 夜間ジョブ `calendar_update_job` を実装し、J-Quants API から差分取得して冪等保存（バックフィルや健全性チェックを含む）を行う。
    - 最大探索日数や先読み・バックフィル・健全性上限などの安全策を実装。

  - ETL パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL の結果を表すデータクラス `ETLResult` を実装（取得件数・保存件数・品質検査結果・エラー集約など）。
    - 差分更新、バックフィル、品質チェックとの統合を想定した設計。J-Quants クライアント経由の取得 & 保存処理を呼び出す枠組みを提供。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチ・ファクター関連 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等の計算関数を追加。
    - DuckDB 上の SQL ウィンドウ関数を活用し、欠損やデータ不足時の扱い（NULL／None）に配慮。
    - 出力は (date, code) をキーとする辞書のリスト形式。

  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（calc_forward_returns）を実装（複数ホライズン対応、入力検証、1クエリ取得）。
    - IC（Information Coefficient）計算（Spearman の順位相関）を実装（rank ユーティリティを含む）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB のみで実装。

- 共通・実装上の配慮
  - 全体的に DuckDB を主要なローカルデータベースとして利用する設計。
  - ルックアヘッドバイアス防止のため、target_date 指定で過去データのみ参照する方針を採用。
  - OpenAI 呼び出しでは JSON Mode を利用し、レスポンスの堅牢なパースと検証を実装。
  - API 失敗時にはスキップやデフォルト（例: macro_sentiment=0.0）で継続するフェイルセーフ設計。
  - DB 書き込みは冪等性を意識して DELETE→INSERT のパターンやトランザクション（BEGIN/COMMIT/ROLLBACK）で実装。
  - テスト容易性のため、API呼び出し箇所（_call_openai_api 等）をモック差替え可能に実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- DuckDB のバージョン差異により executemany の空リストバインドが不安定なため、空パラメータはガードしている。
- OpenAI のレスポンスが期待外のフォーマット（前後に余計なテキストなど）を返す可能性を考慮し、JSON 抽出やパース失敗時のデグレード動作を実装している。
- `strategy` / `execution` / `monitoring` の実装詳細はパッケージ公開インターフェースに含まれるが、ここでは主にデータ・AI・リサーチ・ETL 周りの機能を中心に実装されている。

今後の予定（例）
- strategy 実装の追加（シグナル生成→ポートフォリオ構築）
- execution（kabuステーション）との統合テストと安全装置（資金管理・注文ガード）
- 監視・運用（process supervisor / Line 通知等）の実装強化

--- 

（このCHANGELOGはリポジトリ内の現行ソースコードから推測して作成しています。実際のコミット履歴や公開リリースノートと差異がある可能性があります。）