# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買・データ基盤・リサーチ向けのコア機能群を実装しました。

### Added
- パッケージ初期化
  - パッケージ名 kabusys、バージョンを `__version__ = "0.1.0"` として公開。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に設定（トップレベルのエクスポートを想定）。

- 環境設定・ローダー（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - .env パーサー: コメントや export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント等を適切に処理。
  - 環境値検証/取得ヘルパー: 必須変数チェック（_require）、有効な環境値（development/paper_trading/live）やログレベル検証。
  - 主要設定プロパティを提供（J-Quants トークン、kabu API 設定、Slack トークン・チャンネル、DuckDB/SQLite パスなど）。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む `score_news` を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する `calc_news_window` を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり記事数上限・文字数上限、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - API 呼び出しでの 429/ネットワークエラー/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの不整合（余分なテキストなど）を補正して JSON を抽出する耐性ロジックを実装。
    - テスト容易性のため、内部の OpenAI 呼び出し関数をモックで差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Ｎ225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - ma200_ratio の計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、閾値によるラベル付け、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - OpenAI 呼び出しに対してリトライ/エラー分類を実装（RateLimit, Connection, Timeout, 5xx の扱いなど）。
    - 設計上の方針としてルックアヘッドバイアスを避けるために date.today() を直接参照しない実装とした。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（土日休）でフォールバックする一貫性のあるロジック。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル機能、健全性チェック（極端な未来日付を検出してスキップ）を実装。jquants_client 経由での fetch/save を利用。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETL 実行結果を表す ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー収集などを含む）。
    - 差分更新、バックフィル、品質チェック連携、DuckDB の日付最大値取得ユーティリティ等の基盤実装を追加。
    - ETLResult を data.etl で再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算する関数を追加。データ不足時は None を返す動作。
    - calc_volatility: 20 日 ATR、ATR 比（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0 や欠損なら None）。
    - 全て DuckDB の SQL ベースで実装（外部 API にアクセスしない）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて計算する汎用関数を追加。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算するユーティリティを実装（最小有効レコード数のチェック含む）。
    - rank: 同順位は平均ランクにするランク付けユーティリティを実装（丸めで ties の安定化）。
    - factor_summary: ファクター列ごとの基本統計量（count/mean/std/min/max/median）を計算する関数を実装。
  - research パッケージの __init__ で主要関数を再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等の機密情報は環境変数経由で取得する設計。自動 .env ロードはテスト用に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Implementation details
- LLM 呼び出しについては JSON Mode を使用し、出力の厳密な JSON を期待するが、現実的なノイズに対応するため前後の余計なテキストを抽出してパースする耐性ロジックを含む。
- LLM/API 呼び出しの冪等性や部分失敗に対する保護を考慮し、DB 書き込みは対象コードを絞って DELETE → INSERT を行う（部分失敗時に既存データを保護）。
- DuckDB の executemany に関する互換性（空リスト不可）を考慮したガードコードを実装。
- テストのために内部の OpenAI 呼び出し関数はモック差し替えが容易な実装になっている（unittest.mock.patch）。
- ルックアヘッドバイアス防止のため、多くの関数で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。

今後の予定（例）
- strategy / execution / monitoring モジュールの公開実装（初期はパッケージ構造のみ）。
- jquants_client 実装の統合テストと ETL のエンドツーエンド検証。
- LLM プロンプト・バリデーションの追加改善、API 呼び出しのメトリクス収集。

----- 

（この CHANGELOG は、コードベースの実装内容から推測して作成しています。実際のコミット履歴がある場合はそちらを元に更新してください。）