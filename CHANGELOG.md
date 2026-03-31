# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

注意: 下記の内容は、リポジトリ内のソースコード（src/kabusys 以下）の実装から推測してまとめた初期の変更履歴です。

## [Unreleased]

### Added
- ー

---

## [0.1.0] - 2026-03-31

最初の公開リリース。日本株自動売買／データ基盤・リサーチ・AI支援モジュール群を実装。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = "0.1.0"）。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能（テスト向け）。
  - .env のパース挙動を細かく実装（export プレフィックス、クォート内エスケープ、インラインコメント処理など）。
  - Settings クラスを導入してアプリ設定をプロパティ経由で取得（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル判定等）。
  - 環境変数の必須チェック `_require()` を実装し、未設定時に明確なエラーメッセージを出す。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーを扱うロジックを追加（market_calendar テーブルへのアクセス）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録優先・未登録日は曜日ベースでのフォールバックを採用。
    - カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・保存、バックフィル、健全性チェック）。
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを追加（取得・保存件数、品質チェック結果、エラー概要などを保持）。
    - pipeline モジュールの型を公開（etl から ETLResult を再エクスポート）。
    - ETL 実装方針を反映：差分取得、バックフィル、品質チェックとの連携、DuckDB互換性配慮。

- 研究（research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離（ma200_dev）を計算する calc_momentum を実装。
    - ボラティリティ・流動性指標（20日ATR、ATR比、20日平均売買代金、出来高比）を計算する calc_volatility を実装。
    - バリューファクター（PER、ROE）を計算する calc_value を実装（raw_financials からの最新財務データ参照）。
    - DuckDB SQL を活用した実装（営業日ベースのラグ窓、欠損データ時は None を返す設計）。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズンの LEAD を用いた取得）。
    - IC（Spearman ランク相関）calc_ic 実装。
    - ランク付けユーティリティ rank（同順位は平均ランク）。
    - factor_summary による統計サマリ（count/mean/std/min/max/median）。
  - research パッケージ初期公開 API を整備（calc_momentum, calc_value, calc_volatility, zscore_normalize の再エクスポート等）。

- AI モジュール（kabusys.ai）
  - news_nlp（score_news）
    - raw_news / news_symbols を銘柄別に集約して OpenAI（gpt-4o-mini）の JSON モードでバッチ評価、ai_scores テーブルへ保存する処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数のトリム）を導入。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ実装。エラー時はスキップして継続するフェイルセーフ設計。
    - レスポンスのバリデーションと堅牢な JSON 抽出処理（前後に混入する余計なテキストを許容）。
    - DuckDB executemany の仕様差異への対処（空 params の回避）を実装。
    - テスト用フック: _call_openai_api をモック可能に設計。
  - regime_detector（score_regime）
    - ETF 1321（NIKKEI 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（マクロキーワードフィルタ）、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - API エラーやパース失敗時のフォールバック（macro_sentiment=0.0）などフェイルセーフ設計。
    - テスト用フック同様に _call_openai_api は別実装でモジュール結合を抑制。

### Changed
- ー（初回リリース）

### Fixed
- ー（初回リリース）

### Security
- ー（初回リリース）

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止: news と regime の処理はいずれも内部で datetime.today() / date.today() に依存しないよう設計され、target_date 引数に対して過去ウィンドウのみを参照するようになっている。
- DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT 的保存を意識）しており、部分失敗時に既存データを不必要に消さない工夫がある。
- OpenAI API 呼び出しは JSON Mode を利用しつつも、実運用で混入し得るノイズに耐えるようにレスポンス復元ロジックと厳格なバリデーションを実装。
- DuckDB の互換性・制約（executemany の空リスト不可等）への対応が各所に組み込まれている。
- 環境変数の自動ロードは OS 環境の保護（protected set）や .env/.env.local の優先度制御を考慮している。
- テスト支援として OpenAI 呼び出しや内部 API 呼び出しポイントがモック可能になっている。

---

（補足）実装ファイル群からは strategy / execution / monitoring の具体的実装は見えませんが、パッケージの公開 API にこれらのサブパッケージが含まれることから、今後のリリースで売買ロジック・注文実行・監視機能の実装・公開が予定されていることが推測されます。必要であれば、各モジュール実装に基づくより詳細な変更履歴案を作成します。