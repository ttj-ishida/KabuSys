# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]

- 今後のリリースでの変更点をここに記載します。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。

### Added
- パッケージ基礎
  - パッケージ初期化 (kabusys.__init__): バージョン情報と公開モジュールを定義。
- 設定管理
  - 環境変数/.env ロード機能 (kabusys.config)
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み。
    - export KEY=val 形式、クォート付き値、行内コメント化など実用的な .env パース処理を実装。
    - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 必須環境変数取得のラッパー（_require）と Settings クラスによる型付きアクセサ。
    - 設定項目例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値外は ValueError）。
- AI（自然言語処理）
  - ニュース・NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - チャンク処理（1 API 呼び出しあたり最大 20 銘柄）、1 銘柄あたり最大記事数・文字数でトリム。
    - リトライ（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）と堅牢なレスポンス検証。
    - レスポンス検証では JSON 抽出、results 配列・各要素の code/score チェック、スコアクリップ（±1.0）を実施。
    - DuckDB への冪等書き込み（対象 code のみ DELETE → INSERT）で部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST ベースの前日15:00〜当日08:30 を UTC 表現で返す）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - MA200 乖離の計算ではルックアヘッド防止のため target_date 未満のデータのみ使用。データ不足時は中立 (1.0) を採用してフォールバック。
    - マクロ記事抽出（キーワードマッチ）→ LLM 呼び出し（gpt-4o-mini, JSON 出力）→ リトライ／フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時はロールバック処理とログ。
- リサーチ（ファクター・特徴量探索）
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE） を DuckDB / SQL ベースで算出。
    - データ不足時の None 返却や集計ウィンドウの設計（スキャン範囲バッファ）を実装。
  - 特徴量探索ユーティリティ (kabusys.research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズン検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ：ランク変換、欠損除外、最小件数検査）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research パッケージの公開 API を整理（__all__）。
- データプラットフォーム（DuckDB ベース）
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブル存在有無に応じたフォールバック（DB 優先、未登録日は曜日ベース判定）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。検索範囲上限 (_MAX_SEARCH_DAYS) により無限ループ防止。
    - JPX カレンダー夜間バッチ calendar_update_job：J-Quants から差分取得、バックフィル、健全性チェック、jquants_client を経由した保存。
  - ETL パイプライン基盤 (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラス（target_date、取得/保存件数、品質問題、エラー等）を提供。
    - テーブル存在検査、最大日付取得ユーティリティなど ETL 実装に必要な低レイヤ関数を実装。
    - 差分取得・バックフィル・品質チェック方針を反映した設計（詳細は doc 想定）。
  - jquants_client / quality 等のクライアント層を想定した構成（呼び出し箇所を分離）。
- ロギングとエラーハンドリング
  - 重要箇所での info/debug/warning/exception ログ出力を追加。
  - API レスポンスパース失敗や一時エラーをフェイルセーフで扱い（例外を必ずしも上げない設計）。
- テスト支援
  - AI 呼び出し部分の差し替え（パッチ）を想定した設計でユニットテスト容易性を確保。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- .env 読み込み時に既存の OS 環境変数を保護する仕組み（protected set）を導入し、誤って OS 環境を上書きするリスクを低減。

### Notes / Design decisions
- ルックアヘッドバイアス対策として、全ての「当日基準処理」は内部で datetime.today()／date.today() を直接参照しないよう設計（target_date を明示的に受け取る API を採用）。
- OpenAI 呼び出し箇所はモジュール間で内部プライベート関数を共有せず、各モジュールで独立実装してテストの独立性を確保。
- DuckDB のバージョン差異（executemany の空リスト問題やリスト型バインドの不安定さ）を考慮した互換的実装が行われている。

## Deprecated
- なし

## Removed
- なし

## Security
- なし追加（その他は上記 Security 節参照）

---

作成者: 自動生成（コードベースから推測）  
注: 実際のリリース履歴や日付はプロジェクト運用に合わせて調整してください。