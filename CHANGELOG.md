# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  

※ リリース内容はコードベース（src/ 以下）から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-04

初回公開リリース。日本株向け自動売買／データ基盤／リサーチ／AI 補助モジュール群を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys v0.1.0）。
  - __all__ 経由で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境変数・設定管理 (`kabusys.config`)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込みする仕組みを実装。
  - .env パーサーは以下の特徴を持つ:
    - 空行・コメント行を無視、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを扱う。
    - クォート無し値のインラインコメント処理（# の直前が空白/タブの場合のみコメントと認識）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数を保護（.env の上書き制御）。`.env.local` は上書き優先。
  - Settings クラスを提供し、主要設定値をプロパティで取得:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
    - kabu API: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）
    - LINE: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト data/monitoring.db）
    - 監視: PID / kill flag パスとしきい値（CPU/MEM/DISK 等）
    - 環境種別: `KABUSYS_ENV`（development / paper_trading / live）および `LOG_LEVEL`（DEBUG/INFO/...）の検証
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- AI モジュール（OpenAI 経由、JSON Mode）
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を基に銘柄別に記事を集約し、OpenAI（gpt-4o-mini + JSON mode）でセンチメントを算出。
    - 実装のポイント:
      - 対象ウィンドウ: JST で前日 15:00 ～ 当日 08:30（DB 比較は UTC naive datetime で扱う）
      - バッチ処理: 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）でチャンク化
      - 1 銘柄あたりは最大 10 記事、最大文字数 3000（超過はトリム）
      - リトライ方針: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで最大リトライ
      - レスポンス検証: JSON パース、"results" 配列、各要素の code/score 検証、スコアを ±1.0 にクリップ
      - DB 書き込みは idempotent な置換（対象 code のみ DELETE → INSERT）で部分失敗時の保護を実施
      - API 呼び出し箇所はテスト用に差し替え可能（_call_openai_api を patch 可能）
      - API キー未指定時は ValueError を送出
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（Nikkei 225 連動ETF）の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - 実装のポイント:
      - ma200_ratio の算出は target_date 未満のデータのみを使用（ルックアヘッド回避）
      - マクロ記事はキーワードでフィルタ（最大 20 件）
      - LLM 呼び出しは gpt-4o-mini、JSON レスポンスをパースして macro_sentiment（-1〜1）を取得
      - API 失敗やパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
      - 冪等性を担保（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外を伝播
      - API 呼び出しの差し替えポイントあり（テスト容易性）

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン (`kabusys.data.pipeline` / `kabusys.data.etl`)
    - ETLResult データクラスを追加（実行結果、品質問題、エラー一覧などを格納・辞書化可能）
    - 差分更新、バックフィルの方針、品質チェックの収集設計を反映
    - J-Quants クライアント経由で idempotent に保存（jquants_client を利用）
    - デフォルトの最小データ日付、バックフィル日数等の定数を設定
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar を基に営業日判定・次/前営業日探索・期間内営業日取得・SQ判定を実装
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新する夜間ジョブ（バックフィル・健全性チェックを実装）

- リサーチ / ファクター（`kabusys.research`）
  - ファクター計算 (`kabusys.research.factor_research`)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新報告を使用）
    - 全て DuckDB の prices_daily / raw_financials に対して SQL で完結（本番口座や発注 API へはアクセスしない）
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（存在しない場合は None）
    - calc_ic: スピアマンランク相関（ランクは同順位を平均ランクで扱う）、有効件数 3 未満で None
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 値をランクに変換（丸めで ties 対処）
    - 外部依存（pandas など）を使わず標準ライブラリ + DuckDB で実装

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 秘密情報は環境変数で管理する設計（OpenAI API キー、J-Quants トークン、Kabu API パスワード 等）。
- .env 自動読み込みは OS 環境変数を保護する仕組みを導入。必要に応じて自動読み込みを無効化可能。

### Design / 注意点（使用・移行メモ）
- ルックアヘッドバイアス防止: AI / リサーチ関連は内部で datetime.today() / date.today() を参照せず、明示的な target_date を受け取る設計。
- OpenAI API キーが未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出する。
- OpenAI 呼び出しは gpt-4o-mini + JSON Mode を想定。レスポンスパースや数値バリデーション、クリップ処理を行う。
- DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT 等）し、部分失敗時に既存データを保護する実装。
- テスト容易性:
  - OpenAI 呼び出しは各モジュール内の _call_openai_api を patch して差し替え可能。
  - 環境変数自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- 主要な環境変数（代表）:
  - OPENAI_API_KEY（必須 for AI 機能）
  - JQUANTS_REFRESH_TOKEN（必須 for データ取得）
  - KABU_API_PASSWORD（必須 for 発注連携）
  - DUCKDB_PATH / SQLITE_PATH（DB 保存先、デフォルトあり）
  - KABUSYS_ENV, LOG_LEVEL 等

### Known limitations / 今後想定
- PBR や配当利回り等のバリュー指標は現バージョン未実装（calc_value に注記あり）。
- DuckDB の executemany の挙動に対する互換性処理（空パラメータ回避）を実装済みだが、将来 DuckDB バージョン差異で追加対応が必要になる可能性あり。
- LLM 出力の安定化（JSON モードでも余計な前後テキストが混入するケース）へは部分的に対処済み（最外側の {} を抽出）だが、より堅牢な検証やプロンプト改良が今後の課題。

---

参考: 実装時の主要設計指針
- DB/ETL/Research は本番の取引ロジックと分離し、副作用を起こさない（発注 API へのアクセスなし）。
- API 失敗時は可能な限り継続（フェイルセーフ）、重大な失敗はログに記録して呼び出し元へ伝播する設計。