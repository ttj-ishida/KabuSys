# KabuSys

日本株自動売買システム（KabuSys）の軽量テンプレート／骨組みです。  
本リポジトリは、自動売買に必要となるデータ収集、売買戦略、注文実行、モニタリングの大枠をモジュール分割して提供します。実際の取引ロジックやAPI接続は各モジュール内に実装して拡張してください。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSysは以下の責務を分離したモジュール構成の日本株自動売買システム向けのライブラリ雛形です。

- data: 市場データの取得・キャッシュ・前処理
- strategy: 売買戦略の定義・バックテスト用ロジック
- execution: 注文送信・約定管理・リスク制御
- monitoring: ログ、メトリクス、アラート、ダッシュボード出力

現状はパッケージ構造のみが用意されており、個別コンポーネントはユーザーが実装・拡張することを前提としています。

---

## 機能一覧（テンプレート段階）

- パッケージ化されたモジュール構成（data / strategy / execution / monitoring）
- パッケージバージョン定義（src/kabusys/__init__.py）
- 開発者が実装すべき責務ごとのファイル分割

将来的な実装例（ユーザー側で追加）:

- リアルタイム／過去データ取得クラス（data）
- シグナル生成・ポジション管理クラス（strategy）
- 取引所APIラッパ（execution）
- 実行ログ・アラート・ダッシュボード（monitoring）

---

## セットアップ手順

このリポジトリはPythonパッケージ（srcレイアウト）です。以下のいずれかの方法で開発環境に取り込んでください。

1. 必須要件
   - Python 3.8 以上を推奨
   - 仮想環境の使用を推奨（venv / conda 等）

2. クローン & 仮想環境（例: venv）
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. インストール方法（選択）
   - (A) 開発 editable インストール（プロジェクトに setup.cfg / pyproject.toml がある場合）
     ```
     pip install -e .
     ```
   - (B) PYTHONPATH を使う（簡易）
     ```
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH  # macOS / Linux
     set PYTHONPATH=%CD%\src;%PYTHONPATH%      # Windows (PowerShell/コマンドプロンプトで調整)
     ```
   - (C) 単体スクリプトとして実行する場合は、プロジェクトルートから Python の import が通るように実行してください。

4. 依存関係
   - このテンプレートは外部依存を含みません。必要に応じて requirements.txt や pyproject.toml にパッケージ（例: pandas, numpy, requests, websocket-client 等）を追加してください。

---

## 使い方（基本）

パッケージの読み込みとバージョン確認の例:

```python
import kabusys

print(kabusys.__version__)  # "0.1.0"

# モジュールを参照
from kabusys import data, strategy, execution, monitoring
```

各モジュールは現在空のパッケージです。実装例（テンプレート）として、以下のようなクラス構成を作成して拡張することを想定しています。

例: data モジュールに DataProvider を実装する場合
```python
# src/kabusys/data/provider.py
class DataProvider:
    def get_latest_price(self, symbol: str) -> float:
        """ティッカーの最新価格を返す（実装例）"""
        raise NotImplementedError
```

例: strategy モジュールに BaseStrategy を実装する場合
```python
# src/kabusys/strategy/base.py
class BaseStrategy:
    def on_tick(self, tick):
        """ティックデータを受け取り売買シグナルを返す"""
        raise NotImplementedError

    def on_bar(self, bar):
        """バー（時間足）データで処理"""
        raise NotImplementedError
```

例: execution モジュールに OrderExecutor を実装する場合
```python
# src/kabusys/execution/executor.py
class OrderExecutor:
    def send_order(self, symbol: str, side: str, size: int, price: float = None):
        """注文送信ロジック（API 呼び出し等）"""
        raise NotImplementedError
```

例: monitoring モジュールに Monitor を実装する場合
```python
# src/kabusys/monitoring/monitor.py
class Monitor:
    def log_trade(self, trade):
        """トレードログを保存・出力"""
        raise NotImplementedError

    def send_alert(self, message: str):
        """Slack/メール等へアラート送信"""
        raise NotImplementedError
```

これらを組み合わせて、データ取得 → 戦略判定 → 注文実行 → モニタリング のワークフローを構築します。

---

## ディレクトリ構成

現状の最小構成（src レイアウト）:

- src/
  - kabusys/
    - __init__.py         # パッケージ定義とバージョン
    - data/
      - __init__.py       # data モジュール（データ取得・前処理を実装）
    - strategy/
      - __init__.py       # strategy モジュール（売買戦略を実装）
    - execution/
      - __init__.py       # execution モジュール（注文送信等を実装）
    - monitoring/
      - __init__.py       # monitoring モジュール（ログ・監視を実装）

READMEやドキュメント、テストフォルダ等はプロジェクトルートに配置することを推奨します。将来的には以下を追加することを推奨します：

- tests/               # ユニットテスト
- docs/                # 詳細設計・API ドキュメント
- examples/            # サンプルスクリプト（バックテストやライブ運用例）
- requirements.txt / pyproject.toml / setup.cfg

---

## 開発・拡張ノート

- セキュリティ:
  - 実際の取引APIキーや秘密情報は環境変数またはシークレットマネージャで管理してください。ソースに直接埋め込まないでください。
- テスト:
  - 注文送信等の外部APIを使う部分はモック化してユニットテストを作成してください。
- ロギング:
  - 重要なイベント（注文発行、約定、例外）は必ずログに記録して、監視・リプレイに備えてください。
- リスク管理:
  - ポジション制限、1注文あたりの最大数量、相場急変時のストップロス等の仕組みを実装してください。

---

## 貢献

自由にフォークして実装を進め、プルリクエストを送ってください。実装の際は以下を合わせて提供いただけると助かります。

- 構築手順（README 更新）
- 単体テスト
- 依存関係の明示（requirements.txt / pyproject.toml）
- サンプルの実行例（examples/）

---

## ライセンス

特に記載がない場合はプロジェクトルートに LICENSE ファイルを追加して明示してください（例: MIT, Apache-2.0 等）。

---

必要であれば、サンプル実装（DataProvider / BaseStrategy / OrderExecutor / Monitor）のテンプレートコードや、実際の取引所APIを使った統合サンプルを作成して提供します。どの箇所のサンプルが必要か教えてください。