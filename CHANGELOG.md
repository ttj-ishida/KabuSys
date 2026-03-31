# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

注: 内容はソースコードから推測して作成しています。実際の変更履歴やコミットメッセージとは差異がある場合があります。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買・データプラットフォームの基本コンポーネントを実装。

### Added
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__init__）。公開サブパッケージとして data, strategy, execution, monitoring を定義。
  - バージョン: 0.1.0 を設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）と OS 環境変数の統合読み込み機能を実装。プロジェクトルートを .git または pyproject.toml から探索して自動ロードする仕組みを搭載。
  - .env 行のパーサを実装し、export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等の扱いに対応。
  - 環境変数の上書き制御（override / protected）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化が可能。
  - Settings クラスを実装し、J-Quants / kabu-station / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等の設定プロパティを提供。未設定時は明示的なエラー（ValueError）を投げる保護を実装。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に、対象時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）内のニュースを銘柄毎に集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数トリム、JSON Mode を使った厳密な JSON 応答期待、レスポンス検証、スコアの ±1.0 クリップ等をサポート。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。API エラーやパースエラーはフェイルセーフでスキップし継続。
    - calc_news_window 関数を提供（UTC ナイーブ datetime を返す）。テスト時に OpenAI 呼び出しを差し替え可能な設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む機能を実装。
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）でのセンチメント評価を行う。API リトライ、5xx 特別扱い、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - night batch ジョブ calendar_update_job を実装し、J-Quants から差分取得して market_calendar を冪等保存する処理を提供。バックフィルと健全性チェック（将来日付の異常検出）を実装。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを定義。取得数・保存数・品質チェック結果・エラー一覧を集約。has_errors, has_quality_errors, to_dict を提供。
    - パイプライン用ユーティリティ（テーブル存在チェック、最大日付取得など）の骨組みを実装（差分取得、バックフィル、品質チェックといった設計方針を反映）。

- 研究 / ファクター（kabusys.research）
  - factor_research:
    - モメンタムファクター（1M/3M/6M、200日MA乖離）、ボラティリティ・流動性（20日ATR、平均売買代金、出来高比率）、バリューファクター（PER, ROE）を DuckDB 上で計算する関数（calc_momentum, calc_volatility, calc_value）を実装。
    - SQL を利用して効率的に窓関数等で算出し、欠損やデータ不足条件を適切に扱う。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず純粋な Python / DuckDB で計算。

- ユーティリティ設計上の配慮
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部処理で直接参照しない設計を思想として明示。
  - DuckDB を中心としたローカル分析基盤を想定した実装。
  - DB への書き込みは可能な限り冪等（DELETE→INSERT / ON CONFLICT 等）で行い、部分失敗時の既存データ保護を考慮。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を使う方式。キーマネジメントの詳細は別途運用ガイドで管理することを推奨。

### Known issues / 注意事項
- data.pipeline._get_max_date 関数の実装末尾に不整合（ソースが途中で切れていると思われる箇所）が確認されます（"return date.fro" のような断片）。本箇所は動作しない可能性があるため修正が必要です。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン差異への対応が入っている（空チェックで回避）。実行環境の DuckDB バージョンによって挙動差が出る可能性があるため注意。
- OpenAI 呼び出しは gpt-4o-mini を想定した実装（JSON Mode）。将来の SDK やモデル仕様変更により影響を受ける可能性がある。テストでは _call_openai_api をモックして検証可能。
- .env の自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後や特殊構成では自動ロードがスキップされる場合があるため、環境変数を明示的に設定する運用を推奨。

---

今後の予定（例）
- pipeline の完全実装と end-to-end ETL ワークフロー整備
- strategy / execution / monitoring の具体的な発注ロジックと監視アラートの実装
- 単体テスト・統合テストの拡充、CI パイプライン整備

もし実際のコミット履歴やリリース日に関する正確な情報があれば、これを元に CHANGELOG を正確化します。