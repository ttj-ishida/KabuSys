# Changelog

すべての変更は Keep a Changelog の形式に従っています。重要な変更点は分類して記載しています。

※本リリースはパッケージメタ情報に合わせた最初の公開バージョンです（バージョン 0.1.0）。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開されたサブモジュール: data, research, ai, monitoring, strategy, execution（__all__ による意図的な公開インターフェースの定義）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定値を自動読み込みする仕組みを実装。
  - プロジェクトルート探索: .git または pyproject.toml を基準に自動的にプロジェクトルートを特定（パッケージ配布後も機能するよう設計）。
  - .env パーサー実装: コメントや export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 自動読み込みの優先順位: OS環境変数 > .env.local > .env
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト容易性のため）。
  - 必須環境変数チェック用の _require 関数と Settings クラスを提供。各種設定プロパティ（J-Quants、kabuステーション、Slack、DBパス、環境種別・ログレベルなど）を定義。
  - Settings に環境値検証（KABUSYS_ENV 有効値チェック、LOG_LEVEL チェック）と is_live / is_paper / is_dev の補助プロパティを追加。

- AI モジュール（src/kabusys/ai/）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols をソースに、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込むワークフローを実装。
    - ニュース収集ウィンドウの計算（JST 基準 → UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/リクエスト）・トークン肥大化対策（記事数上限と文字数トリム）を実装。
    - JSON モード（厳密な JSON 出力）での呼び出し、レスポンスのバリデーション（構造チェック、型チェック、未知コード無視、スコアのクリップ）を実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ実装。失敗時は個別チャンクをスキップし他チャンクは継続するフェイルセーフ設計。
    - DuckDB への書き込みは部分置換（該当 code の DELETE → INSERT）することで部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api により patchable）。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - prices_daily から MA200 乖離を計算するロジック（ルックアヘッド防止のため target_date 未満のデータのみ参照）。
    - マクロキーワードで raw_news をフィルタしてタイトルを収集し、OpenAI でマクロセンチメントを算出（記事なしは LLM 呼び出しを行わず macro_sentiment=0.0）。
    - OpenAI 呼び出しのリトライ、エラー種別別のハンドリング（RateLimit/接続/タイムアウト/5xx 等）、レスポンスパース失敗時は安全に macro_sentiment=0.0 を採用。
    - score_regime は冪等性を保った DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - テスト容易性のため _call_openai_api は差し替え可能。

- データ管理（src/kabusys/data/）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を前提とした営業日判定ロジックを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が不完全または未登録の場合は曜日（土日）ベースでフォールバックし、一貫した動作を保つ設計。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得して market_calendar を冪等に更新する夜間ジョブ実装。バックフィル・健全性チェック（将来日付の異常検知）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装し、ETL 実行結果の構造化（取得件数、保存件数、品質問題、エラー一覧など）を提供。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取引日調整ロジックなどを実装。
  - etl の公開インターフェースで ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- 研究用（research）モジュール（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum、Value、Volatility（および一部流動性指標）を SQL + Python で計算する関数を実装: calc_momentum, calc_value, calc_volatility。
    - 各関数は DuckDB の prices_daily / raw_financials を参照して日付・コード単位の結果リストを返す設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、およびファクター統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で実装。
  - research パッケージの __init__ で主要関数を再エクスポート。

### Changed
- 設計指針（全体ドキュメント的実装反映）
  - 重大設計方針が実装に反映されていることを明記（ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない、外部サービス呼び出しはフェイルセーフにする、DuckDB の互換性考慮など）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT や ON CONFLICT 相当）を意識した実装に。

### Fixed
- 安全性／堅牢性向上
  - .env 読み込みでのファイル読み取り失敗時に warnings.warn で通知して処理継続するように（例外でプロセス停止させない）。
  - ai モジュールにおける OpenAI API 呼び出しでの多様なエラーに対して個別に対処し、フェイルセーフ（0.0 返却、チャンクスキップ等）する実装により、外部 API 障害時もプロセス継続可能に。
  - DuckDB の executemany に空リストを渡すと問題になる点に対応し、空チェックを入れてから executemany を呼ぶように修正（部分書き込みでの互換性向上）。

### Documentation / Notes
- 各モジュールに設計方針と処理フローを詳細にコメントで記載。特に AI・ETL・カレンダー・リサーチ周りで、ルックアヘッドバイアス防止や部分失敗時の保護方針が明確に説明されています。
- テスト容易性: OpenAI 呼び出しや環境自動読み込みの無効化フラグなど、ユニットテストで差し替え可能なポイントを用意。

### Security
- 環境変数の扱いに注意する旨の設計（必須トークンは _require で明示的にチェック）。自動ロードの上書きから OS 環境変数を保護する protected キーセットを実装。

---

この CHANGELOG は、コードベースから推測できる実装と設計意図に基づいて作成しています。実際の変更履歴（コミットメッセージ等）とは差異がある場合があります。必要であれば各ファイルの差分やコミット履歴に基づくより正確な CHANGELOG を作成します。