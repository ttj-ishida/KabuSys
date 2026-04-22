# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-22

### 追加 (Added)
- プロジェクト初期リリース。
- 実行用スクリプトを追加:
  - run_execution.py — ExecutionEngine の起動スクリプト。KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite を使って本番 DB と分離する。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト: 60秒）。監視は常に本番用 sqlite_path を使用する設計。
- 設定関連 CLI を追加:
  - config_setup.py — 対話式 .env 作成/更新ウィザード（入力ヒント、既存値の再利用、シークレットマスク表示）。
  - validate_config.py — 環境変数および config/*.yaml の起動前チェック CLI（--strict オプションで警告を失敗扱いにできる）。
- 設定管理モジュールを追加:
  - config.py — .env/.env.local の自動ロード（OS 環境変数優先、.env.local は上書き）、.env の柔軟なパース処理（export 形式、クォート文字列、エスケープ、インラインコメント処理等）、Settings クラス（環境変数取得ラッパー）。
  - Settings に paper trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）や監視/閾値関連プロパティを実装。
- ロギング/プロセス制御ユーティリティを追加:
  - utils/logging_setup.py — stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ作成失敗時のフォールバック処理、ログレベル解決ロジックを実装。
  - utils/process_priority.py — Windows/Linux(macOS/FreeBSD 含む) を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。アクセス拒否等の例外は警告にフォールバック。
- Portfolio 構築モジュールを追加（メモリ内純関数群）:
  - portfolio/portfolio_builder.py — 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights)。
  - portfolio/risk_adjustment.py — セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py — 銘柄ごとの発注株数計算 (calc_position_sizes)。allocation_method（risk_based / equal / score）対応、単元株丸め、aggregate cap によるスケールダウンと残差処理を実装。
- tools:
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定する（閾値はソースに定義）。
- research:
  - research/factor_research.py — ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の設計を実装）。（calc_momentum などの実装が含まれているが、一部スニペットは継続実装前提）

### 変更 (Changed)
- 起動スクリプト共通の挙動:
  - 起動時に最初にプロセス優先度を "high" に設定するよう統一。
  - SQLite と DuckDB の両方を利用する設計。DuckDB は分析用、SQLite は監視/履歴保存用として明確に分離。
- .env 自動ロードの挙動:
  - OS 環境変数を保護するために .env/.env.local 読み込み時に既存 OS 環境変数を上書きしない（.env.local は override=True だが protected な OS キーは上書きしない）。
- ロギング:
  - stdout を StreamHandler に用いる（stderr ではなく stdout） — cron/task scheduler などからのリダイレクトを想定。
  - 日次ローテーションで最大 30 日分のログを保持。

### 修正 (Fixed)
- 環境変数の妥当性チェックやフォールバックを強化:
  - MONITOR_POLL_INTERVAL のパースで不正値（0以下や非整数）を検出した場合、警告を出してデフォルトにフォールバックする処理を実装。
  - PAPER_FILL_MODE の許容値チェックを実装し、不正値は ValueError を発生させるようにした。
  - Settings.env / LOG_LEVEL の不正値検出と明確なエラーメッセージを追加。
- validate_config:
  - PyYAML 未インストール時に YAML 検証をスキップして警告を出すことで起動時の致命的な ImportError を防止。
  - config/*.yaml が存在しない場合は警告を出す（生成スクリプトへの案内コメントあり）。
- position_sizing:
  - cost_buffer を導入して手数料・スリッページを保守的に見積もることで aggregate cap 判定の精度を向上。
  - lot_size による丸めロジックや残余キャッシュを用いた再配分ロジックを実装し、期待しない小数丸めの偏りを低減。

### 既知の問題 / 注意点 (Known issues / Notes)
- research/factor_research.py はファクター計算の設計を含むが、ソース末尾で calc_momentum の実装が途中で切れている（継続実装が必要）。
- apply_sector_cap の価格欠損（price == 0.0）の扱いについて TODO コメントあり。将来的な価格フォールバック（前日終値など）の導入を検討している。
- process_priority / set_cpu_affinity は権限不足や非対応 OS 下で例外を捕捉し警告にフォールバックするが、実際に期待した優先度変更が行われていない可能性を運用上把握しておくこと。
- .env ファイルは機密情報を含むため必ず Git 管理下にコミットしない旨の注意書きを config_setup の生成ファイルヘッダに含めている。

---

(以降のリリースでは、各コンポーネントのテスト追加・未実装箇所の完成・エラーハンドリング強化・ドキュメント補完を予定しています。)