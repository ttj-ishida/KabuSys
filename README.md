# KabuSys

KabuSys は日本株向けの自動売買システムの雛形（ボイラープレート）です。モジュール化された設計により、データ取得・戦略定義・注文実行・監視を分離して開発できます。本リポジトリは最小限のパッケージ構成（パッケージのスケルトン）を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

このプロジェクトは、自動売買システムを構築するための基本構成を提供します。以下の4つの主要コンポーネントを想定しています。

- data: 市場データの取得・整形（例：板情報・板寄せ・日足・出来高など）
- strategy: エントリー・エグジットを決定する戦略ロジック
- execution: 証券会社API等を介した注文送信・約定管理
- monitoring: ログ記録・メール／チャット通知・ダッシュボード反映

現状はパッケージの雛形のみで、各モジュールの具体的実装は含まれていません。開発者はこの骨組みをベースに実装・拡張してください。

---

## 機能一覧（想定）

- モジュール化されたシステム構成（data / strategy / execution / monitoring）
- パッケージ化された Python モジュール（src 配下）
- 戦略や実行ロジックを独立して開発できる設計

※ 現在はインターフェースの雛形のみで、具体的なAPI実装（kabuステーションや証券会社連携）は含まれていません。

---

## 要件

- Python 3.8 以上（推奨: 3.8↑）
- 仮想環境の使用を推奨

必要な外部ライブラリはまだ定義されていません。各自で依存関係（例: requests、pandas、websocket-client 等）を追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate     # macOS / Linux
   .venv\Scripts\activate        # Windows
   ```

3. 開発環境へインストール（2通りの方法）

   a) パッケージ化済みの場合（pyproject.toml / setup.py がある場合）
   ```
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

   b) 現状のようにパッケージのみがある場合（ソースを直接使う）
   - 実行時に src を PYTHONPATH に含める（例: 開発環境）
     ```
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH   # macOS / Linux
     set PYTHONPATH=%cd%\src;%PYTHONPATH%       # Windows (PowerShell では別形式)
     ```
   - あるいは実行スクリプトの sys.path に src を追加してください。

4. 依存パッケージが増える場合は requirements.txt を用意し、インストールしてください。
   ```
   python -m pip install -r requirements.txt
   ```

---

## 使い方（基本）

パッケージは以下の名前空間を提供します。

- kabusys.data
- kabusys.strategy
- kabusys.execution
- kabusys.monitoring

バージョン確認やモジュール参照の例：
```python
from kabusys import __version__, data, strategy, execution, monitoring

print("KabuSys version:", __version__)
print("available modules:", [m for m in ('data','strategy','execution','monitoring')])
# 直接モジュールオブジェクトの内容を確認
print(dir(data))
```

各モジュールは現在スケルトンです。以下は実際に拡張する際のサンプルテンプレート例です。

- data モジュールのサンプルクラス
```python
# src/kabusys/data/provider.py
class DataProvider:
    """市場データを提供するベースクラス（サンプル）"""
    def connect(self):
        raise NotImplementedError

    def get_latest_price(self, symbol: str):
        raise NotImplementedError
```

- strategy モジュールのサンプルクラス
```python
# src/kabusys/strategy/base.py
class Strategy:
    """戦略のベースクラス（サンプル）"""
    def on_tick(self, tick):
        """ティックデータを受け取って注文判断を行う"""
        raise NotImplementedError
```

- execution モジュールのサンプルクラス
```python
# src/kabusys/execution/engine.py
class ExecutionEngine:
    """注文送信・管理のベースクラス（サンプル）"""
    def send_order(self, order):
        raise NotImplementedError

    def cancel_order(self, order_id):
        raise NotImplementedError
```

- monitoring モジュールのサンプルクラス
```python
# src/kabusys/monitoring/logger.py
class Monitor:
    """ログ・通知のベースクラス（サンプル）"""
    def info(self, msg: str):
        print(msg)

    def alert(self, msg: str):
        # 例えばメールやSlack通知などを実装
        raise NotImplementedError
```

これらを実装して、メインの実行ループで DataProvider -> Strategy -> ExecutionEngine -> Monitor の順で連携させます。

---

## ディレクトリ構成

現状の最小構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py           # パッケージ初期化 (バージョン等)
    - data/
      - __init__.py
      # （データプロバイダ実装をここに追加）
    - strategy/
      - __init__.py
      # （戦略クラスをここに追加）
    - execution/
      - __init__.py
      # （注文実行ロジックをここに追加）
    - monitoring/
      - __init__.py
      # （監視・通知ロジックをここに追加）

ファイル（現状）
- src/kabusys/__init__.py
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 拡張・開発のヒント

- 各モジュールにベースクラスを定義しておくと、実装の切り替え（モック／本番）が容易になります。
- 注文実行は非同期処理やリトライ、エラーハンドリングが重要です。テスト時に外部依存を切り離せるように抽象化してください。
- 監視は例外や重要イベントを即時通知できるようにしておくと安全性が高まります（Slack、メール、ログ集約など）。
- 単体テスト・統合テストを用意し、CI で自動実行することを推奨します。

---

## 貢献・ライセンス

このリポジトリは雛形のため、自由にフォークして拡張してください。ライセンスや貢献ルールはプロジェクト方針に合わせて追加してください（MIT や Apache 2.0 などを推奨）。

---

README は最小限のドキュメントですが、実装が進んだら以下を充実させてください。

- 具体的な API ドキュメント（関数・クラスの引数・返り値）
- 設定ファイル（API キーや接続設定）の取り扱い
- 実行手順（デプロイ方法・定期実行の設定）
- テスト手順と CI 設定

必要であれば、この README を元により詳細な設計ドキュメントやサンプル実装を作成します。どの機能から実装したいか教えてください。