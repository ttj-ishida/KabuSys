# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本リリースノートはコードベースから推測して作成しています（コメント・実装方針・定数等を元に要約）。

## Unreleased
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-04

初回公開リリース。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring（__all__ に定義）

- 環境変数・設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 解析の堅牢化:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応
  - 環境設定ラッパー Settings を提供:
    - J-Quants / kabu API / LINE Messaging / データベースパス（DuckDB/SQLite）/監視関連（PID/kill flag/閾値）/システム環境（env, log_level）等のプロパティ
    - env と log_level の値検証（許容値チェック）
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH 等）を用意

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出して ai_scores テーブルへ書き込む機能を実装
  - 処理の特徴:
    - JST 基準のニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC へ変換）
    - 1 銘柄あたり記事数・文字数上限（トークン肥大化対策）
    - 最大バッチサイズ（20 銘柄）でのチャンク送信
    - レート制限、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライ
    - API レスポンスのバリデーション（JSON 抽出、results 構造、既知コードフィルタ、スコア数値検証）
    - スコアは ±1.0 にクリップ
    - 書き込みは冪等性を考慮（該当 code の DELETE → INSERT を実行、部分失敗時に他コードを保護）
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次書き込み
  - 処理の特徴:
    - prices_daily と raw_news の参照による MA 計算とマクロ記事抽出
    - マクロニュースはキーワードフィルタ（複数キーワード）で抽出、LLM で -1.0～1.0 のマクロセンチメントを推定（gpt-4o-mini）
    - LLM 呼び出しにはリトライ・バックオフを実装、失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）
    - score_regime は冪等に DB へ書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
    - ルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ参照、datetime.today() 不使用）

- 研究用ファクター・特徴量モジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比などを計算。必要サンプル未満は None。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 や欠損時は None）。最新財務データ取得は report_date <= target_date の最新を採用。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（IC）を計算。十分な有効レコードがない場合は None を返す。
    - factor_summary: 各ファクター列の基本統計（count, mean, std, min, max, median）を計算。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties 対策）

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - market_calendar テーブルに基づく営業日判定・次/前営業日取得・期間内営業日一覧・SQ 判定等を提供
    - DB 登録優先、未登録日は曜日ベースでフォールバック（週末を非営業日）
    - calendar_update_job: J-Quants から差分取得 → market_calendar へ冪等保存（バックフィル・健全性チェックあり）
    - 最大探索日数やバックフィル日数等の定数で無限ループや過度の取得を防止
  - pipeline / ETL:
    - ETLResult データクラスを公開（etl.py 経由で再エクスポート）
    - ETL パイプライン設計方針の実装（差分取得、backfill、品質チェックの集約、id_token 注入可能）
    - ETLResult により品質問題・エラー情報を構造化して返却
  - 補助関数:
    - テーブル存在チェック、最大日付取得等のユーティリティ実装

- 外部依存・設計上の注意点（実装から明示）
  - OpenAI SDK（gpt-4o-mini）を利用。API 呼び出しは JSON Mode（厳密な JSON 出力を前提）で行う。
  - DuckDB を利用した SQL 処理（DuckDB のバージョンに依存する挙動を考慮した実装）
  - ルックアヘッドバイアス回避の設計（date 引数ベース、datetime.today() を直接参照しない）
  - フェイルセーフな動作: API 失敗時は例外を上げずフォールバック（0.0 やスキップ）して継続する箇所が多い

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし
- 注意点: OpenAI API キー・外部トークン等の機密情報は環境変数経由で管理する想定（Settings._require による必須チェックがある箇所あり）。

---

## 既知の制約と注意事項（実装から推測）
- 多くの関数は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）の存在を前提としている。テーブルスキーマ不整合や未作成時の挙動に注意。
- 時刻管理は UTC naive / JST の変換ルールを内部で扱っているが、タイムゾーン付き datetime を渡すと想定外の挙動となる可能性がある（実装は date / naive datetime を使用）。
- OpenAI のレスポンスが厳密な JSON でない場合に備えてパーサで救済処理を行っているが、誤った出力が多いとスコア欠落が発生する。
- DuckDB 0.10 系での executemany の空パラメータ制約に対応する分岐があるため、DuckDB のバージョン差異に注意。

---

（以上）もし特定の変更点をより詳細に記載したい場合（例: 各モジュールごとの細かなログ出力・例外処理の振る舞い等）、対象モジュールを指定してください。