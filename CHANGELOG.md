# Changelog

すべての変更は Keep a Changelog 規約に従って記載します。  
このプロジェクトはまだ初期リリースです。

履歴のフォーマット:
- 変更は Unreleased またはバージョン別にまとめます。
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。

## [Unreleased]

（このブランチ/作業中の変更はここに記載されます）

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ識別子とバージョンを `src/kabusys/__init__.py` に実装（__version__ = "0.1.0"）。
  - モジュール公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数読み込み（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
  - `.env` と `.env.local` の読み込み順序（OS 環境変数 > .env.local > .env）をサポート。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env パース処理の強化:
    - `export KEY=val` 形式をサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理を実装。
    - インラインコメントの取り扱い（クォート有無での差分処理）を実装。
  - 読み込み時の上書き制御（override）と OS 環境変数の保護（protected set）を提供。
  - 必須環境変数を取得する `_require` と、Settings クラス（J-Quants・kabu API・Slack・DB パス・環境種別・ログレベル等のプロパティ）を実装。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値集合）を実装。`is_live`/`is_paper`/`is_dev` ユーティリティを提供。

- AI 関連（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを生成。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）を UTC 変換して安全に扱う `calc_news_window` を実装。
    - バッチ処理（最大 20 銘柄/チャンク）および 1 銘柄あたりの文字数/記事数トリミングを実装（トークン膨張対策）。
    - API 呼び出しでのリトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score の検証、スコアの ±1.0 クリップ）。
    - DuckDB の executemany の互換性を考慮した部分置換（対象コードのみ DELETE → INSERT）で idempotent な書き込みを実現。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を組み合わせて日次で `market_regime` を判定・保存。
    - マクロニュース抽出用のキーワードリストと、LLM 呼び出し（gpt-4o-mini）での JSON レスポンス処理を実装。
    - API 呼び出し失敗やパース失敗時にフェイルセーフとして macro_sentiment=0.0 を採用。
    - 慎重設計: ルックアヘッドバイアス防止（datetime.today/date.today 参照を避け、date 未満条件でクエリ）を徹底。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理を実装し、例外時に ROLLBACK を試みる。

- 研究・ファクター計算（kabusys.research）
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - DuckDB SQL を活用し、外部 API に依存しない純粋なデータ処理を提供。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得。horizons 検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマン ρ（ランク相関）を計算（有効レコードが 3 件未満なら None）。
    - rank: 同順位を平均ランクで処理する安定したランク化実装（丸め処理で ties 検出漏れを防止）。
    - factor_summary: カウント・平均・標準偏差・最小・最大・中央値などの統計サマリーを計算。
  - 研究向けユーティリティ: `kabusys.research.__init__` で zscore_normalize（kabusys.data.stats）を含む複数関数を再エクスポート。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job`（J-Quants から差分取得 → 保存）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定 API を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。DB 登録がある場合は DB 値を優先する一貫した挙動を採用。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェック（未来日に対する安全性）を実装。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを実装して ETL の取得/保存件数、品質問題、エラー概要を集約可能に。
    - 差分更新・バックフィル・品質チェックの方針をコードに反映。
  - ETL 便宜の再エクスポート（etl モジュールで ETLResult をエクスポート）。

- ロギングと堅牢性
  - 各モジュールで詳細なログメッセージを追加（info/warning/debug/exception）。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で扱い、ROLLBACK 失敗時には警告ログを出力。
  - OpenAI 呼び出し部分は例外を抑制してフェイルセーフにする設計（部分失敗を許容）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 `OPENAI_API_KEY` でも取得可能。未設定時は明確に例外を投げる仕様により誤設定を早期検出。
- `.env` 読み込みにおいて OS 環境変数の上書きを防ぐ保護機構（protected set）を実装。

---

開発上の注意点・設計上の制約
- ルックアヘッドバイアス防止のため、内部処理は現在日時の自動参照を避け、外部から与えられる target_date に基づいて計算する設計になっています。
- DuckDB のバージョン互換性（executemany の空リスト制約、リスト型バインドの安定性）に配慮した実装を行っています。
- OpenAI 呼び出しは JSON Mode を利用するため、レスポンスの前後に余計なテキストが混ざるケースへの復元ロジックを導入しています。
- テスト容易性のため、内部の API 呼び出し関数（例: _call_openai_api）を patch 可能に設計しています。

（必要であれば、各モジュールの公開 API サマリやマイグレーション手順を別途追加できます。）